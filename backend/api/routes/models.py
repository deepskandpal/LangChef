from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import boto3
import re

from backend.database import get_db
from backend.services.auth_service import get_current_user, AWSSSOService, validate_aws_credentials
from backend.models import User
from backend.config import settings
from backend.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

@router.get("/available", response_model=List[Dict[str, Any]])
async def get_available_models(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth requirement
):
    """Get all available models, including AWS Bedrock models if credentials are valid."""
    models = []
    
    try:
        logger.info(f"Fetching available models for user: {current_user.username}")
        logger.info(f"User AWS credentials from DB: access_key={bool(current_user.aws_access_key_id)}, secret_key={bool(current_user.aws_secret_access_key)}, token={bool(current_user.aws_session_token)}")
        
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
        
        # We'll populate Claude models dynamically from AWS Bedrock
        bedrock_models = []
        
        try:
            # Check if user has valid AWS credentials
            is_aws_valid = await validate_aws_credentials(current_user)
            logger.info(f"AWS credentials validation result: {is_aws_valid}")
            
            # Include Claude models only if AWS credentials are valid
            if is_aws_valid:
                # Try to get the actual available models from AWS Bedrock
                try:
                    # Use the current user's AWS credentials to create the Bedrock client
                    boto3_session = boto3.Session(
                        aws_access_key_id=current_user.aws_access_key_id,
                        aws_secret_access_key=current_user.aws_secret_access_key,
                        aws_session_token=current_user.aws_session_token,
                        region_name=settings.AWS_REGION
                    )
                    
                    # Create bedrock client
                    logger.info(f"Creating Bedrock client with user credentials: {current_user.username}")
                    bedrock_client = boto3_session.client('bedrock')
                    
                    # Get list of available foundation models
                    logger.info("Calling Bedrock list_foundation_models")
                    response = bedrock_client.list_foundation_models()
                    
                    if 'modelSummaries' in response:
                        available_model_ids = [model['modelId'] for model in response['modelSummaries']]
                        logger.info(f"Available Bedrock models: {available_model_ids}")
                        
                        # Filter for only Claude models and create model entries dynamically
                        claude_model_ids = [model_id for model_id in available_model_ids if model_id.startswith('anthropic.claude')]
                        logger.info(f"Available Claude models: {claude_model_ids}")
                        
                        # Function to generate friendly name from Claude model ID
                        def get_claude_model_info(model_id):
                            model_name_map = {
                                # Basic mapping for well-known Claude models
                                'anthropic.claude-instant-v1': 'Claude Instant',
                                'anthropic.claude-v2': 'Claude 2',
                                'anthropic.claude-v2:1': 'Claude 2.1',
                            }
                            
                            # Always include the full model ID as a suffix for debugging
                            model_id_short = model_id.split('.')[-1]  # Remove the 'anthropic.' prefix
                            
                            # Special handling for Claude 3.5 and 3.7 models
                            if 'anthropic.claude-3-5-' in model_id:
                                # Extract the model variant (sonnet, haiku)
                                variant = ""
                                if 'sonnet' in model_id:
                                    variant = "Sonnet"
                                elif 'haiku' in model_id:
                                    variant = "Haiku"
                                elif 'opus' in model_id:
                                    variant = "Opus"
                                
                                # Extract version info and date
                                version = ""
                                date_part = ""
                                
                                # Look for a date in the format YYYYMMDD
                                date_match = re.search(r'(\d{8})', model_id)
                                if date_match:
                                    date_part = date_match.group(1)
                                
                                # Look for version indicator
                                if 'v1:0' in model_id:
                                    version = "v1"
                                elif 'v2:0' in model_id:
                                    version = "v2"
                                elif 'v3:0' in model_id:
                                    version = "v3"
                                
                                # Create a unique friendly name that includes all important info
                                friendly_name = f"Claude 3.5 {variant}"
                                if version:
                                    friendly_name += f" {version}"
                                if date_part:
                                    friendly_name += f" ({date_part})"
                                
                                logger.info(f"SPECIAL MODEL: Parsed '{model_id}' to '{friendly_name}'")
                                return {
                                    "id": model_id,
                                    "name": friendly_name,
                                    "provider": "aws_bedrock",
                                    "description": f"{friendly_name} via AWS Bedrock",
                                    "supported_features": ["text-generation", "chat"]
                                }
                            
                            # Special handling for Claude 3.7 models - similar approach
                            if 'anthropic.claude-3-7-' in model_id:
                                # Extract the model variant (sonnet, haiku)
                                variant = ""
                                if 'sonnet' in model_id:
                                    variant = "Sonnet"
                                elif 'haiku' in model_id:
                                    variant = "Haiku"
                                elif 'opus' in model_id:
                                    variant = "Opus"
                                
                                # Extract version info and date
                                version = ""
                                date_part = ""
                                
                                # Look for a date in the format YYYYMMDD
                                date_match = re.search(r'(\d{8})', model_id)
                                if date_match:
                                    date_part = date_match.group(1)
                                
                                # Look for version indicator
                                if 'v1:0' in model_id:
                                    version = "v1"
                                elif 'v2:0' in model_id:
                                    version = "v2"
                                elif 'v3:0' in model_id:
                                    version = "v3"
                                
                                # Create a unique friendly name that includes all important info
                                friendly_name = f"Claude 3.7 {variant}"
                                if version:
                                    friendly_name += f" {version}"
                                if date_part:
                                    friendly_name += f" ({date_part})"
                                
                                logger.info(f"SPECIAL MODEL: Parsed '{model_id}' to '{friendly_name}'")
                                return {
                                    "id": model_id,
                                    "name": friendly_name,
                                    "provider": "aws_bedrock",
                                    "description": f"{friendly_name} via AWS Bedrock",
                                    "supported_features": ["text-generation", "chat"]
                                }
                            
                            # For models not in the map, generate a friendly name
                            if model_id in model_name_map:
                                friendly_name = model_name_map[model_id]
                            else:
                                # Parse the model ID to create a friendly name
                                if model_id.startswith('anthropic.claude-'):
                                    # Strip the 'anthropic.claude-' prefix
                                    name_part = model_id[len('anthropic.claude-'):]
                                    
                                    # Get version suffix if present (e.g., v1:0, v2:0)
                                    version_suffix = ""
                                    if '-v' in name_part:
                                        version_parts = name_part.split('-v')
                                        if len(version_parts) > 1:
                                            v_suffix = version_parts[1]
                                            if ':' in v_suffix:
                                                v_num = v_suffix.split(':', 1)[0]
                                                version_suffix = f" v{v_num}"
                                    
                                    # Handle versioning in the id itself (if in format date-vX:0)
                                    if ':' in name_part:
                                        parts = name_part.split(':')
                                        if len(parts) > 1:
                                            name_part = parts[0]
                                            # If we have a version in the date portion (like 20241022-v2)
                                            if '-v' in name_part and not version_suffix:
                                                date_parts = name_part.split('-v')
                                                if len(date_parts) > 1:
                                                    name_part = date_parts[0]
                                                    version_suffix = f" v{date_parts[1]}"
                                    
                                    # Extract date info if available
                                    date_part = ""
                                    date_match = re.search(r'(\d{8})', name_part)
                                    if date_match:
                                        date_part = f" ({date_match.group(1)})"
                                        # Remove the date from the name part to avoid duplication
                                        name_part = re.sub(r'\d{8}', '', name_part).strip('-')
                                    
                                    # Format nicely (e.g., "3-sonnet-20240229" -> "Claude 3 Sonnet")
                                    parts = name_part.split('-')
                                    
                                    # Handle special cases for subversions
                                    if len(parts) >= 1:
                                        # Extract model version (3, 3.5, 3.7, etc.)
                                        model_version = parts[0]
                                        
                                        # For Claude 3 models with variants (sonnet, haiku, opus)
                                        if len(parts) >= 2 and parts[1] in ['sonnet', 'haiku', 'opus']:
                                            variant = parts[1].capitalize()
                                            friendly_name = f"Claude {model_version} {variant}{version_suffix}{date_part}"
                                        else:
                                            # If no variant, just use the version number
                                            friendly_name = f"Claude {model_version}{version_suffix}{date_part}"
                                    else:
                                        # Just clean up the name as a fallback
                                        friendly_name = ' '.join(p.capitalize() for p in parts)
                                        friendly_name = f"Claude {friendly_name}{version_suffix}{date_part}"
                                else:
                                    friendly_name = model_id.split('.')[-1].replace('-', ' ').title()
                                    # Add the model ID as a suffix for uniqueness
                                    if ':' in model_id:
                                        version_part = model_id.split(':')[-1]
                                        friendly_name += f" v{version_part}"
                            
                            logger.info(f"Standard model: Parsed '{model_id}' to '{friendly_name}'")
                            
                            return {
                                "id": model_id,
                                "name": friendly_name,
                                "provider": "aws_bedrock",
                                "description": f"{friendly_name} via AWS Bedrock",
                                "supported_features": ["text-generation", "chat"]
                            }
                        
                        # Generate model entries for all available Claude models
                        bedrock_models = []
                        
                        # Manual mapping for certain model IDs to ensure correct display names
                        model_id_to_name = {
                            'anthropic.claude-3-5-sonnet-20240620-v1:0': 'Claude 3.5 Sonnet v1',
                            'anthropic.claude-3-5-sonnet-20241022-v2:0': 'Claude 3.5 Sonnet v2',
                            'anthropic.claude-3-7-sonnet-20250219-v1:0': 'Claude 3.7 Sonnet v1',
                            'anthropic.claude-3-5-haiku-20241022-v1:0': 'Claude 3.5 Haiku v1'
                        }
                        
                        # Keep track of which models we've already processed to avoid duplicates
                        processed_model_ids = set()
                        
                        # Process all available Claude models
                        for model_id in claude_model_ids:
                            # Skip if we've already processed this model ID
                            if model_id in processed_model_ids:
                                logger.info(f"Skipping duplicate model ID: {model_id}")
                                continue
                            
                            # Mark as processed
                            processed_model_ids.add(model_id)
                            
                            # Check if we have a direct mapping for this model ID
                            if model_id in model_id_to_name:
                                friendly_name = model_id_to_name[model_id]
                                logger.info(f"Using direct mapping for '{model_id}' -> '{friendly_name}'")
                                bedrock_models.append({
                                    "id": model_id,
                                    "name": friendly_name,
                                    "provider": "aws_bedrock",
                                    "description": f"{friendly_name} via AWS Bedrock",
                                    "supported_features": ["text-generation", "chat"]
                                })
                            else:
                                # Use the general function for other models
                                bedrock_models.append(get_claude_model_info(model_id))
                        
                        logger.info(f"Created {len(bedrock_models)} Claude model entries")
                        
                        # Log specific models we're interested in
                        for model_id in claude_model_ids:
                            if '3-5' in model_id or '3-7' in model_id or '3-5-sonnet' in model_id or '3-7-sonnet' in model_id:
                                friendly_name = get_claude_model_info(model_id)['name']
                                logger.info(f"Special model mapping: '{model_id}' -> '{friendly_name}'")
                        
                except Exception as bedrock_error:
                    logger.error(f"Error checking Bedrock models: {bedrock_error}")
                    # Set empty list if there was an error
                    bedrock_models = []
            else:
                logger.warning(f"AWS credentials invalid for user {current_user.username}. Not fetching AWS Bedrock models.")
        except Exception as validation_error:
            logger.error(f"Error validating AWS credentials: {validation_error}")
            # Set empty list if there was an error
            bedrock_models = []
        
        # Add the dynamically generated Claude models to the list
        models.extend(bedrock_models)
        logger.info(f"Returning {len(models)} available models")
        
        return models
        
    except HTTPException as http_exc:
        # Re-raise HTTP exceptions (like auth errors)
        logger.error(f"HTTP exception in get_available_models: {http_exc}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        # Return at least the default models instead of failing completely
        if not models:
            models = default_models
            logger.info(f"Returning {len(models)} default models due to error")
        return models

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
        region = request.get('region', 'us-east-1')
        
        logger.info(f"Running playground model: {model_id} with provider: {model_provider} for user: {current_user.username}")
        
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
        
        # Verify credentials for AWS Bedrock models
        if model_provider == 'aws_bedrock':
            is_aws_valid = await validate_aws_credentials(current_user)
            if not is_aws_valid:
                logger.error(f"User {current_user.username} has invalid AWS credentials for Bedrock")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="AWS credentials are invalid or expired",
                    headers={"X-AWS-Session-Expired": "true"}
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
            # Create a Bedrock runtime client using user credentials from the database
            logger.info(f"Creating Bedrock runtime client for region {region} with user credentials")
            boto3_session = boto3.Session(
                aws_access_key_id=current_user.aws_access_key_id,
                aws_secret_access_key=current_user.aws_secret_access_key,
                aws_session_token=current_user.aws_session_token,
                region_name=region
            )
            
            bedrock_runtime = boto3_session.client('bedrock-runtime')
            
            import time
            import json
            
            start_time = time.time()
            logger.info(f"Making API call to Bedrock with model: {model_id}")
            
            try:
                # Handle Claude 3 models separately (using Messages API)
                if 'claude-3' in model_id:
                    logger.info(f"Using invoke_model API for Claude 3 model: {model_id}")
                    
                    # For Claude 3 models, we need to use the 'messages' format but through invoke_model
                    request_body = {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "messages": []
                    }
                    
                    # Add system prompt if provided
                    if prompt and prompt.strip():
                        request_body["system"] = prompt
                    
                    # Add user message
                    request_body["messages"] = [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": input_data
                                }
                            ]
                        }
                    ]
                    
                    logger.info(f"Claude 3 request body: {request_body}")
                    
                    try:
                        bedrock_response = bedrock_runtime.invoke_model(
                            modelId=model_id,
                            body=json.dumps(request_body)
                        )
                        
                        end_time = time.time()
                        logger.info(f"Successful response from invoke_model API for {model_id}")
                        
                        # Parse response from Claude 3
                        response_body = json.loads(bedrock_response['body'].read())
                        logger.info(f"Claude 3 response structure: {response_body}")
                        
                        # Extract content from the response
                        output_text = ""
                        if 'content' in response_body and isinstance(response_body['content'], list) and len(response_body['content']) > 0:
                            # New format where content is directly in response
                            output_text = response_body['content'][0].get('text', '')
                            logger.info(f"Extracted response text from content, length: {len(output_text)}")
                        elif 'message' in response_body and 'content' in response_body['message']:
                            # Format with message wrapper
                            content_list = response_body['message']['content']
                            if isinstance(content_list, list) and len(content_list) > 0:
                                output_text = content_list[0].get('text', '')
                                logger.info(f"Extracted response text from message.content, length: {len(output_text)}")
                        
                        # If we still don't have text, log warning
                        if not output_text:
                            output_text = "No response content from Claude 3 model"
                            logger.warning(f"Could not extract response text from Claude 3: {response_body}")
                        
                        # Calculate metrics
                        latency_ms = (end_time - start_time) * 1000
                        
                        # Use usage data from the response if available
                        if 'usage' in response_body:
                            input_tokens = response_body['usage'].get('input_tokens', 0)
                            output_tokens = response_body['usage'].get('output_tokens', 0)
                            logger.info(f"Token usage from API: input={input_tokens}, output={output_tokens}")
                        else:
                            # Estimate token counts (rough estimate)
                            input_tokens = len(prompt.split()) + len(input_data.split())
                            output_tokens = len(output_text.split())
                            logger.info(f"Estimated token usage: input={input_tokens}, output={output_tokens}")
                        
                        # Update response
                        response['text'] = output_text
                        response['latency_ms'] = latency_ms
                        response['usage'] = {
                            'prompt_tokens': input_tokens,
                            'completion_tokens': output_tokens,
                            'total_tokens': input_tokens + output_tokens
                        }
                    except Exception as claude_error:
                        logger.error(f"Error using invoke_model API: {claude_error}")
                        raise Exception(f"Error calling Claude 3 model: {claude_error}")
                    
                # Handle older Claude models and other models using invoke_model
                else:
                    # Prepare the request body based on the model
                    if 'anthropic.claude-v' in model_id or 'anthropic.claude-instant' in model_id:
                        # Claude 2 and Claude Instant format
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
                    
                    logger.info(f"Using invoke_model API for model: {model_id}")
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
                
                logger.info(f"Bedrock API call successful. Tokens: {response['usage']['total_tokens']}, Latency: {latency_ms:.2f}ms")
                
                # Calculate cost (rough estimate)
                # Define rate function instead of a static dictionary
                def get_model_rate(model_id):
                    # Default rates if we can't determine the model
                    default_rate = {'input': 0.001, 'output': 0.002}
                    
                    # Helper to match model prefix
                    def model_matches(prefix):
                        return model_id.startswith(prefix)
                    
                    # Claude 3 models
                    if model_matches('anthropic.claude-3-sonnet'):
                        return {'input': 0.003, 'output': 0.015}
                    elif model_matches('anthropic.claude-3-haiku'):
                        return {'input': 0.00025, 'output': 0.00125}
                    elif model_matches('anthropic.claude-3-opus'):
                        return {'input': 0.015, 'output': 0.075}
                    elif model_matches('anthropic.claude-3-5-sonnet'):
                        return {'input': 0.003, 'output': 0.015}
                    elif model_matches('anthropic.claude-3-7-sonnet'):
                        return {'input': 0.005, 'output': 0.025}
                    
                    # Claude 2 models
                    elif model_matches('anthropic.claude-instant-v'):
                        return {'input': 0.0008, 'output': 0.0024}
                    elif model_matches('anthropic.claude-v2'):
                        return {'input': 0.008, 'output': 0.024}
                    
                    # Llama models
                    elif model_matches('meta.llama'):
                        return {'input': 0.00195, 'output': 0.00195}
                    
                    # Mistral models
                    elif model_matches('mistral.mistral-7b'):
                        return {'input': 0.0002, 'output': 0.0002}
                    elif model_matches('mistral.mixtral-8x7b'):
                        return {'input': 0.0007, 'output': 0.0007}
                    
                    # Use default rate if no match
                    return default_rate
                
                rate = get_model_rate(model_id)
                input_cost = (response['usage']['prompt_tokens'] / 1000) * rate['input']
                output_cost = (response['usage']['completion_tokens'] / 1000) * rate['output']
                response['cost'] = input_cost + output_cost
                
            except Exception as bedrock_error:
                logger.error(f"Error calling Bedrock API: {bedrock_error}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error calling AWS Bedrock: {str(bedrock_error)}"
                )
            
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
    except HTTPException as http_exc:
        # Re-raise HTTP exceptions
        logger.error(f"HTTP exception in run_playground_model: {http_exc}")
        raise http_exc
    except Exception as e:
        logger.error(f"Error in run_playground_model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run model: {str(e)}"
        ) 