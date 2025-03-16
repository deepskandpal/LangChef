from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import boto3
import logging

from ...utils import get_db
from ...services.auth_service import get_current_user, AWSSSOService, validate_aws_credentials
from ...models import User
from ...config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/available", response_model=List[Dict[str, Any]])
async def get_available_models(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth requirement
):
    """Get all available models, including AWS Bedrock models if credentials are valid."""
    models = []
    
    try:
        # Check if user has valid AWS credentials
        is_aws_valid = await validate_aws_credentials(current_user)
        
        # Default models - OpenAI
        default_models = [
            {
                "id": "gpt-4",
                "name": "GPT-4",
                "provider": "openai",
                "description": "OpenAI GPT-4 model",
                "supported_features": ["text-generation", "chat"]
            },
            {
                "id": "gpt-3.5-turbo",
                "name": "GPT-3.5 Turbo",
                "provider": "openai",
                "description": "OpenAI GPT-3.5 Turbo model",
                "supported_features": ["text-generation", "chat"]
            }
        ]
        
        models.extend(default_models)
        
        # Check for AWS Bedrock models - only add if AWS credentials are valid
        if is_aws_valid:
            bedrock_models = [
                {
                    "id": "anthropic.claude-v2",
                    "name": "Claude 2",
                    "provider": "aws_bedrock",
                    "description": "Anthropic Claude 2 via AWS Bedrock",
                    "supported_features": ["text-generation", "chat"]
                },
                {
                    "id": "anthropic.claude-instant-v1",
                    "name": "Claude Instant",
                    "provider": "aws_bedrock",
                    "description": "Anthropic Claude Instant via AWS Bedrock",
                    "supported_features": ["text-generation", "chat"]
                },
                {
                    "id": "anthropic.claude-3-sonnet-20240229-v1:0",
                    "name": "Claude 3 Sonnet",
                    "provider": "aws_bedrock",
                    "description": "Anthropic Claude 3 Sonnet via AWS Bedrock",
                    "supported_features": ["text-generation", "chat"]
                },
                {
                    "id": "anthropic.claude-3-haiku-20240307-v1:0",
                    "name": "Claude 3 Haiku",
                    "provider": "aws_bedrock",
                    "description": "Anthropic Claude 3 Haiku via AWS Bedrock",
                    "supported_features": ["text-generation", "chat"]
                },
                {
                    "id": "anthropic.claude-3-opus-20240229-v1:0",
                    "name": "Claude 3 Opus",
                    "provider": "aws_bedrock",
                    "description": "Anthropic Claude 3 Opus via AWS Bedrock",
                    "supported_features": ["text-generation", "chat"]
                }
            ]
            
            # Try to validate which models are actually available by checking with Bedrock
            try:
                # Use the current user's AWS credentials to create the Bedrock client
                boto3_session = boto3.Session(
                    aws_access_key_id=current_user.aws_access_key_id,
                    aws_secret_access_key=current_user.aws_secret_access_key,
                    aws_session_token=current_user.aws_session_token,
                    region_name=settings.AWS_REGION
                )
                
                # Create bedrock client
                bedrock_client = boto3_session.client('bedrock')
                
                # Get list of available foundation models
                response = bedrock_client.list_foundation_models()
                
                if 'modelSummaries' in response:
                    available_model_ids = [model['modelId'] for model in response['modelSummaries']]
                    
                    # Filter bedrock_models to only include available ones
                    bedrock_models = [
                        model for model in bedrock_models 
                        if model['id'] in available_model_ids
                    ]
                
                # Add filtered Bedrock models to the models list
                models.extend(bedrock_models)
                
            except Exception as bedrock_error:
                logger.error(f"Error checking Bedrock models: {bedrock_error}")
                # We'll still return the default models
        
        return models
        
    except HTTPException as http_exc:
        # Re-raise HTTP exceptions (like auth errors)
        raise http_exc
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        # Return a proper error response instead of a 500
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch models: {str(e)}"
        )

@router.post("/playground/run", response_model=Dict[str, Any])
async def run_playground_model(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """Run a model in the playground."""
    try:
        # Extract request parameters
        prompt = request.get('prompt', '')
        input_data = request.get('input', '')
        model_id = request.get('model_id', '')
        model_provider = request.get('model_provider', '')
        temperature = request.get('temperature', 0.7)
        max_tokens = request.get('max_tokens', 1000)
        
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Prompt is required"
            )
        
        if not model_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Model ID is required"
            )
        
        # Initialize response
        response = {
            'text': '',
            'model': model_id,
            'usage': {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            },
            'latency_ms': 0,
            'cost': 0
        }
        
        # Handle different model providers
        if model_provider == 'aws_bedrock':
            # Create a Bedrock runtime client
            bedrock_runtime = boto3.client(
                'bedrock-runtime',
                region_name='us-east-1',  # Default region
                aws_access_key_id=current_user.aws_access_key_id,
                aws_secret_access_key=current_user.aws_secret_access_key,
                aws_session_token=current_user.aws_session_token
            )
            
            # Prepare the request body based on the model
            if 'anthropic' in model_id:
                # Claude format
                request_body = {
                    'prompt': f"{prompt}\n\nHuman: {input_data}\n\nAssistant:",
                    'max_tokens_to_sample': max_tokens,
                    'temperature': temperature,
                    'top_p': 1.0,
                    'stop_sequences': ["\n\nHuman:"]
                }
            elif 'meta.llama' in model_id:
                # Llama format
                request_body = {
                    'prompt': f"<s>[INST] {prompt} [/INST] {input_data} </s>",
                    'max_gen_len': max_tokens,
                    'temperature': temperature,
                    'top_p': 1.0
                }
            else:
                # Generic format
                request_body = {
                    'inputText': f"{prompt}\n\n{input_data}",
                    'textGenerationConfig': {
                        'maxTokenCount': max_tokens,
                        'temperature': temperature,
                        'topP': 1.0
                    }
                }
            
            # Call Bedrock API
            import time
            import json
            
            start_time = time.time()
            bedrock_response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(request_body)
            )
            end_time = time.time()
            
            # Parse response
            response_body = json.loads(bedrock_response['body'].read())
            
            # Extract text based on model
            if 'anthropic' in model_id:
                output_text = response_body.get('completion', '')
            elif 'meta.llama' in model_id:
                output_text = response_body.get('generation', '')
            else:
                output_text = response_body.get('results', [{}])[0].get('outputText', '')
            
            # Calculate metrics
            latency_ms = (end_time - start_time) * 1000
            
            # Estimate token counts (this is a rough estimate)
            prompt_tokens = len(prompt.split()) + len(input_data.split())
            completion_tokens = len(output_text.split())
            
            # Update response
            response['text'] = output_text
            response['latency_ms'] = latency_ms
            response['usage'] = {
                'prompt_tokens': prompt_tokens,
                'completion_tokens': completion_tokens,
                'total_tokens': prompt_tokens + completion_tokens
            }
            
            # Calculate cost (rough estimate)
            rates = {
                'anthropic.claude-3-sonnet-20240229-v1:0': {'input': 0.003, 'output': 0.015},
                'anthropic.claude-3-haiku-20240307-v1:0': {'input': 0.00025, 'output': 0.00125},
                'anthropic.claude-3-opus-20240229-v1:0': {'input': 0.015, 'output': 0.075},
                'anthropic.claude-instant-v1': {'input': 0.0008, 'output': 0.0024},
                'anthropic.claude-v2': {'input': 0.008, 'output': 0.024},
                'anthropic.claude-v2:1': {'input': 0.008, 'output': 0.024},
                'meta.llama2-70b-chat-v1': {'input': 0.00195, 'output': 0.00195},
                'meta.llama3-70b-instruct-v1:0': {'input': 0.00195, 'output': 0.00195},
                'mistral.mistral-7b-instruct-v0:2': {'input': 0.0002, 'output': 0.0002},
                'mistral.mixtral-8x7b-instruct-v0:1': {'input': 0.0007, 'output': 0.0007},
            }
            
            rate = rates.get(model_id, {'input': 0.001, 'output': 0.002})
            input_cost = (prompt_tokens / 1000) * rate['input']
            output_cost = (completion_tokens / 1000) * rate['output']
            response['cost'] = input_cost + output_cost
            
        elif model_provider == 'openai':
            # For OpenAI models, we'll just return a mock response for now
            # In a real implementation, you would call the OpenAI API
            response['text'] = f"This is a mock response from {model_id}. In a real implementation, this would call the OpenAI API."
            response['latency_ms'] = 500
            response['usage'] = {
                'prompt_tokens': len(prompt.split()) + len(input_data.split()),
                'completion_tokens': 50,
                'total_tokens': len(prompt.split()) + len(input_data.split()) + 50
            }
            
            # Calculate cost
            rates = {
                'gpt-4o': {'input': 0.005, 'output': 0.015},
                'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
                'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
            }
            
            rate = rates.get(model_id, {'input': 0.0005, 'output': 0.0015})
            input_cost = (response['usage']['prompt_tokens'] / 1000) * rate['input']
            output_cost = (response['usage']['completion_tokens'] / 1000) * rate['output']
            response['cost'] = input_cost + output_cost
        
        return response
    except Exception as e:
        logger.error(f"Error in run_playground_model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run model: {str(e)}"
        ) 