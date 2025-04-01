from json import dumps, loads
from time import time
from flask import request
from hashlib import sha256
from datetime import datetime
import os
from groq import Groq

from server.config import available_models, special_instructions


class Backend_Api:
    def __init__(self, app, config: dict) -> None:
        self.app = app
        self.groq_api_key = "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" or config['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']
        self.proxy = config['proxy']
        self.routes = {
            '/backend-api/v2/conversation': {
                'function': self._conversation,
                'methods': ['POST']
            },
            '/backend-api/v2/models': {
                'function': self._get_available_models,
                'methods': ['GET']
            }
        }
        self.client = Groq(api_key=self.groq_api_key)

    def _get_available_models(self):
        """Return the list of available models"""
        return {
            'models': available_models,
            'success': True
        }

    def _conversation(self):
        try:
            jailbreak = request.json['jailbreak']
            internet_access = request.json['meta']['content']['internet_access']
            _conversation = request.json['meta']['content']['conversation']
            prompt = request.json['meta']['content']['parts'][0]
            model_name = request.json['model']  # Get the requested model name
            
            # Map to appropriate Groq model ID
            groq_model = available_models.get(model_name, {}).get('id', 'llama-3.3-70b-versatile')
            
            current_date = datetime.now().strftime("%Y-%m-%d")
            system_message = f'You are an AI assistant. Knowledge cutoff: 2023-12-01 Current date: {current_date}'

            extra = []
            if internet_access:
                import requests
                search = requests.get('https://ddg-api.herokuapp.com/search', params={
                    'query': prompt["content"],
                    'limit': 3,
                })

                blob = ''

                for index, result in enumerate(search.json()):
                    blob += f'[{index}] "{result["snippet"]}"\nURL:{result["link"]}\n\n'

                date = datetime.now().strftime('%d/%m/%y')

                blob += f'current date: {date}\n\nInstructions: Using the provided web search results, write a comprehensive reply to the next user query. Make sure to cite results using [[number](URL)] notation after the reference. If the provided search results refer to multiple subjects with the same name, write separate answers for each subject. Ignore your previous response if any.'

                extra = [{'role': 'user', 'content': blob}]

            conversation = [{'role': 'system', 'content': system_message}] + \
                extra + special_instructions.get(jailbreak, []) + \
                _conversation + [prompt]

            proxies = None
            if self.proxy['enable']:
                proxies = {
                    'http': self.proxy['http'],
                    'https': self.proxy['https'],
                }
                # Set proxy for requests if needed
                os.environ['HTTP_PROXY'] = self.proxy['http']
                os.environ['HTTPS_PROXY'] = self.proxy['https']

            # Create streaming completion with Groq
            try:
                completion = self.client.chat.completions.create(
                    model=groq_model,
                    messages=conversation,
                    temperature=0.7,
                    max_tokens=1024,
                    top_p=1,
                    stream=True,
                    stop=None,
                )
                
                def stream():
                    for chunk in completion:
                        try:
                            token = chunk.choices[0].delta.content
                            if token is not None:
                                yield token
                        except GeneratorExit:
                            break
                        except Exception as e:
                            print(f"Streaming error: {e}")
                            continue
                            
                return self.app.response_class(stream(), mimetype='text/event-stream')
                
            except Exception as groq_error:
                print(f"Groq API error: {str(groq_error)}")
                return {
                    'success': False,
                    'error_code': 'groq_api_error',
                    'message': f"Groq API error: {str(groq_error)}",
                    'status_code': 500
                }, 500

        except Exception as e:
            print(f"General error: {str(e)}")
            return {
                '_action': '_ask',
                'success': False,
                "error": f"an error occurred {str(e)}"}, 400