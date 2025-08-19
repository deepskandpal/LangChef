from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union
import tiktoken
import openai
import boto3
import json
from backend.models.experiment import ModelProvider

class BaseLLMService(ABC):
    """Base class for LLM services."""
    
    @abstractmethod
    def generate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in the text."""
        pass
    
    @abstractmethod
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost of the request."""
        pass

class OpenAIService(BaseLLMService):
    """Service for interacting with OpenAI models."""
    
    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        self.model_name = model_name
        self.config = config or {}
        
        # Set up pricing based on model
        self.pricing = {
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4o": {"input": 0.005, "output": 0.015},
        }
        
        # Default to gpt-3.5-turbo pricing if model not found
        if self.model_name not in self.pricing:
            self.pricing[self.model_name] = self.pricing["gpt-3.5-turbo"]
    
    def generate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a response from OpenAI."""
        prompt = input_data.get("prompt", "")
        data = input_data.get("data", {})
        
        # Prepare messages
        messages = [
            {"role": "system", "content": prompt}
        ]
        
        # Add user message from data
        if isinstance(data, dict) and "text" in data:
            messages.append({"role": "user", "content": data["text"]})
        elif isinstance(data, str):
            messages.append({"role": "user", "content": data})
        else:
            messages.append({"role": "user", "content": json.dumps(data)})
        
        # Get model parameters from config
        params = {
            "model": self.model_name,
            "messages": messages,
            "temperature": self.config.get("temperature", 0.7),
            "max_tokens": self.config.get("max_tokens", 1000),
            "top_p": self.config.get("top_p", 1.0),
            "frequency_penalty": self.config.get("frequency_penalty", 0.0),
            "presence_penalty": self.config.get("presence_penalty", 0.0)
        }
        
        # Call OpenAI API
        response = openai.chat.completions.create(**params)
        
        # Extract and return the response
        return {
            "text": response.choices[0].message.content,
            "model": self.model_name,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
    
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in the text."""
        try:
            encoding = tiktoken.encoding_for_model(self.model_name)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")  # Default encoding
        
        return len(encoding.encode(text))
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost of the request in USD."""
        model_pricing = self.pricing.get(self.model_name, self.pricing["gpt-3.5-turbo"])
        
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
        
        return input_cost + output_cost

class BedrockService(BaseLLMService):
    """Service for interacting with AWS Bedrock models."""
    
    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        self.model_name = model_name
        self.config = config or {}
        
        # Set up pricing based on model
        self.pricing = {
            "anthropic.claude-v2": {"input": 0.008, "output": 0.024},
            "anthropic.claude-3-sonnet-20240229-v1:0": {"input": 0.003, "output": 0.015},
            "anthropic.claude-3-haiku-20240307-v1:0": {"input": 0.00125, "output": 0.00625},
            "meta.llama2-13b-chat-v1": {"input": 0.00075, "output": 0.00075},
            "meta.llama2-70b-chat-v1": {"input": 0.00195, "output": 0.00195},
        }
        
        # Default to Claude pricing if model not found
        if self.model_name not in self.pricing:
            self.pricing[self.model_name] = self.pricing["anthropic.claude-v2"]
        
        # Initialize Bedrock client
        self.bedrock_runtime = boto3.client("bedrock-runtime")
    
    def generate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a response from AWS Bedrock."""
        prompt = input_data.get("prompt", "")
        data = input_data.get("data", {})
        
        # Prepare the prompt based on model
        if "anthropic" in self.model_name:
            # Claude format
            if isinstance(data, dict) and "text" in data:
                full_prompt = f"{prompt}\n\nHuman: {data['text']}\n\nAssistant:"
            elif isinstance(data, str):
                full_prompt = f"{prompt}\n\nHuman: {data}\n\nAssistant:"
            else:
                full_prompt = f"{prompt}\n\nHuman: {json.dumps(data)}\n\nAssistant:"
            
            request_body = {
                "prompt": full_prompt,
                "max_tokens_to_sample": self.config.get("max_tokens", 1000),
                "temperature": self.config.get("temperature", 0.7),
                "top_p": self.config.get("top_p", 1.0),
                "stop_sequences": self.config.get("stop_sequences", ["\n\nHuman:"])
            }
        
        elif "meta.llama" in self.model_name:
            # Llama format
            if isinstance(data, dict) and "text" in data:
                full_prompt = f"<s>[INST] {prompt} [/INST] {data['text']} </s>"
            elif isinstance(data, str):
                full_prompt = f"<s>[INST] {prompt} [/INST] {data} </s>"
            else:
                full_prompt = f"<s>[INST] {prompt} [/INST] {json.dumps(data)} </s>"
            
            request_body = {
                "prompt": full_prompt,
                "max_gen_len": self.config.get("max_tokens", 1000),
                "temperature": self.config.get("temperature", 0.7),
                "top_p": self.config.get("top_p", 1.0)
            }
        
        else:
            # Generic format
            if isinstance(data, dict) and "text" in data:
                full_prompt = f"{prompt}\n\n{data['text']}"
            elif isinstance(data, str):
                full_prompt = f"{prompt}\n\n{data}"
            else:
                full_prompt = f"{prompt}\n\n{json.dumps(data)}"
            
            request_body = {
                "inputText": full_prompt,
                "textGenerationConfig": {
                    "maxTokenCount": self.config.get("max_tokens", 1000),
                    "temperature": self.config.get("temperature", 0.7),
                    "topP": self.config.get("top_p", 1.0)
                }
            }
        
        # Call Bedrock API
        response = self.bedrock_runtime.invoke_model(
            modelId=self.model_name,
            body=json.dumps(request_body)
        )
        
        # Parse response
        response_body = json.loads(response["body"].read())
        
        # Extract text based on model
        if "anthropic" in self.model_name:
            output_text = response_body.get("completion", "")
        elif "meta.llama" in self.model_name:
            output_text = response_body.get("generation", "")
        else:
            output_text = response_body.get("results", [{}])[0].get("outputText", "")
        
        # Count tokens for usage
        input_tokens = self.count_tokens(full_prompt)
        output_tokens = self.count_tokens(output_text)
        
        return {
            "text": output_text,
            "model": self.model_name,
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }
        }
    
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in the text."""
        # Use tiktoken for approximation
        try:
            if "anthropic" in self.model_name:
                encoding = tiktoken.get_encoding("cl100k_base")  # Claude uses similar tokenization to GPT-4
            else:
                encoding = tiktoken.get_encoding("p50k_base")  # Default for other models
        except KeyError:
            encoding = tiktoken.get_encoding("p50k_base")  # Fallback
        
        return len(encoding.encode(text))
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost of the request in USD."""
        model_pricing = self.pricing.get(self.model_name, self.pricing["anthropic.claude-v2"])
        
        input_cost = (input_tokens / 1000) * model_pricing["input"]
        output_cost = (output_tokens / 1000) * model_pricing["output"]
        
        return input_cost + output_cost

class CustomService(BaseLLMService):
    """Service for interacting with custom models."""
    
    def __init__(self, model_name: str, config: Optional[Dict[str, Any]] = None):
        self.model_name = model_name
        self.config = config or {}
        
        # Set up default pricing
        self.pricing = {
            "input": self.config.get("input_price_per_1k", 0.001),
            "output": self.config.get("output_price_per_1k", 0.002)
        }
    
    def generate(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a response from a custom model."""
        # This is a placeholder for custom model integration
        # In a real implementation, this would call your custom model API
        
        prompt = input_data.get("prompt", "")
        data = input_data.get("data", {})
        
        # Prepare the prompt
        if isinstance(data, dict) and "text" in data:
            full_prompt = f"{prompt}\n\n{data['text']}"
        elif isinstance(data, str):
            full_prompt = f"{prompt}\n\n{data}"
        else:
            full_prompt = f"{prompt}\n\n{json.dumps(data)}"
        
        # Count tokens for usage
        input_tokens = self.count_tokens(full_prompt)
        
        # Placeholder response
        output_text = f"This is a placeholder response from the custom model {self.model_name}."
        output_tokens = self.count_tokens(output_text)
        
        return {
            "text": output_text,
            "model": self.model_name,
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
            }
        }
    
    def count_tokens(self, text: str) -> int:
        """Count the number of tokens in the text."""
        # Use tiktoken for approximation
        encoding = tiktoken.get_encoding("p50k_base")
        return len(encoding.encode(text))
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate the cost of the request in USD."""
        input_cost = (input_tokens / 1000) * self.pricing["input"]
        output_cost = (output_tokens / 1000) * self.pricing["output"]
        
        return input_cost + output_cost

def get_llm_service(
    provider: ModelProvider, 
    model_name: str, 
    config: Optional[Dict[str, Any]] = None
) -> BaseLLMService:
    """Factory function to get the appropriate LLM service."""
    if provider == ModelProvider.OPENAI:
        return OpenAIService(model_name, config)
    elif provider == ModelProvider.AWS_BEDROCK:
        return BedrockService(model_name, config)
    elif provider == ModelProvider.ANTHROPIC:
        # For direct Anthropic API (not through Bedrock)
        # This would need a separate implementation
        return CustomService(model_name, config)
    elif provider == ModelProvider.HUGGINGFACE:
        # For HuggingFace API
        # This would need a separate implementation
        return CustomService(model_name, config)
    elif provider == ModelProvider.CUSTOM:
        return CustomService(model_name, config)
    else:
        raise ValueError(f"Unsupported provider: {provider}") 