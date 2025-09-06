import os
import time
import json
from django.conf import settings
from typing import Dict, List, Optional, Tuple
import logging

try:
    from semilattice import Semilattice
    SEMILATTICE_AVAILABLE = True
except ImportError:
    SEMILATTICE_AVAILABLE = False
    import requests

logger = logging.getLogger(__name__)


def serialize_sdk_response(obj):
    """Convert SDK response objects to JSON-serializable dictionaries"""
    try:
        # First try to convert to JSON and back to catch serialization issues early
        return json.loads(json.dumps(obj, default=_sdk_object_handler))
    except Exception as e:
        logger.warning(f"Failed to serialize SDK response: {e}")
        # Fallback to simple string representation
        return {"serialization_error": str(obj), "error": str(e)}


def _sdk_object_handler(obj):
    """Handle SDK objects that can't be serialized by default JSON encoder"""
    if hasattr(obj, '__dict__'):
        # Convert object to dict, handling nested objects
        result = {}
        for key, value in obj.__dict__.items():
            if key.startswith('_'):
                continue  # Skip private attributes
            try:
                # Try to serialize the value
                json.dumps(value)
                result[key] = value
            except TypeError:
                # If value can't be serialized, convert it recursively
                result[key] = _sdk_object_handler(value)
        return result
    elif isinstance(obj, list):
        return [_sdk_object_handler(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: _sdk_object_handler(v) for k, v in obj.items()}
    else:
        # For any other non-serializable object, convert to string
        return str(obj)


class SemilatticeAPIClient:
    """Client for interacting with Semilattice API using official SDK when available"""
    
    def __init__(self):
        self.api_key = settings.SEMILATTICE_API_KEY
        self.base_url = settings.SEMILATTICE_BASE_URL
        
        if SEMILATTICE_AVAILABLE:
            # Use official SDK (preferred)
            self.client = Semilattice(api_key=self.api_key)
            self.use_sdk = True
        else:
            # Fallback to HTTP requests
            self.headers = {
                'authorization': self.api_key,
                'content-type': 'application/json',
            }
            self.use_sdk = False
    
    def get_population(self, population_id: str) -> Dict:
        """
        Get population details from Semilattice API
        GET /v1/populations/{population_id}
        """
        try:
            if self.use_sdk:
                # Using SDK - note: this might not be available in all SDK versions
                # If not available, we'll use HTTP fallback
                try:
                    response = self.client.populations.get(population_id)
                    return {
                        "success": True,
                        "data": response.data,
                        "errors": getattr(response, 'errors', [])
                    }
                except AttributeError:
                    # SDK doesn't have populations.get, fallback to HTTP
                    return self._get_population_http(population_id)
            else:
                return self._get_population_http(population_id)
                
        except Exception as e:
            logger.error(f"Error fetching population {population_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_population_http(self, population_id: str) -> Dict:
        """HTTP fallback for getting population"""
        response = requests.get(
            f"{self.base_url}/v1/populations/{population_id}",
            headers={'authorization': self.api_key},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        return {
            "success": True,
            "data": data.get("data", {}),
            "errors": data.get("errors", [])
        }
    
    def simulate_answer(self, population_id: str, question: str, 
                       question_type: str, answer_options: Optional[List[str]] = None) -> Dict:
        """
        Start a simulation for a question against a population
        POST /v1/answers - following official SDK pattern
        """
        try:
            # Build the answers payload according to API spec
            answers_payload = {
                "question": question,
                "question_options": {"question_type": question_type},
            }
            
            # Add answer options for choice questions
            if question_type in ['single-choice', 'multiple-choice'] and answer_options:
                answers_payload["answer_options"] = answer_options
            
            if self.use_sdk:
                # Use official SDK (preferred method)
                result = self.client.answers.simulate(
                    population_id=population_id,
                    answers=answers_payload
                )
                
                # Handle SDK response format - SDK returns objects, not dicts
                if hasattr(result, 'data'):
                    data_list = result.data if isinstance(result.data, list) else [result.data]
                    first_answer = data_list[0] if data_list else None
                else:
                    first_answer = result
                
                # Extract values using attribute access, not dict access
                answer_id = None
                status = None
                
                if first_answer:
                    answer_id = getattr(first_answer, 'id', None)
                    status = getattr(first_answer, 'status', None)
                    
                    # Debug logging to understand SDK response structure
                    logger.info(f"SDK Response - first_answer type: {type(first_answer)}")
                    logger.info(f"SDK Response - answer_id: {answer_id}, status: {status}")
                
                # Serialize SDK response for JSON storage
                try:
                    serialized_data = serialize_sdk_response(result.data if hasattr(result, 'data') else result)
                    logger.info("Successfully serialized SDK response")
                except Exception as serialization_error:
                    logger.error(f"Failed to serialize SDK response: {serialization_error}")
                    # Fallback to basic info
                    serialized_data = {
                        "answer_id": answer_id,
                        "status": status,
                        "serialization_error": str(serialization_error)
                    }
                
                return {
                    "success": True,
                    "answer_id": answer_id,
                    "status": status,
                    "data": serialized_data,
                    "errors": getattr(result, 'errors', [])
                }
            else:
                # HTTP fallback
                return self._simulate_answer_http(population_id, answers_payload)
                
        except Exception as e:
            logger.error(f"Error simulating answer: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _simulate_answer_http(self, population_id: str, answers_payload: dict) -> Dict:
        """HTTP fallback for answer simulation"""
        payload = {
            "population_id": population_id,
            "answers": answers_payload
        }
        
        response = requests.post(
            f"{self.base_url}/v1/answers",
            headers=self.headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Handle both single answer and array responses
        if isinstance(data.get("data"), list):
            first_answer = data["data"][0] if data["data"] else {}
        else:
            first_answer = data.get("data", {})
        
        return {
            "success": True,
            "answer_id": first_answer.get("id"),
            "status": first_answer.get("status"),
            "data": data,
            "errors": data.get("errors", [])
        }
    
    def get_answer_status(self, answer_id: str) -> Dict:
        """
        Get the current status and results of a simulation
        GET /v1/answers/{answer_id} - following official SDK pattern
        """
        try:
            if self.use_sdk:
                # Use official SDK
                result = self.client.answers.get(answer_id)
                
                # Handle SDK response format - SDK returns objects, not dicts
                answer_data = result.data if hasattr(result, 'data') else result
                
                # Extract values using attribute access for SDK objects
                status = getattr(answer_data, 'status', None)
                simulated_answer_percentages = getattr(answer_data, 'simulated_answer_percentages', None)
                
                # Debug logging
                logger.info(f"SDK get_answer_status - answer_data type: {type(answer_data)}")
                logger.info(f"SDK get_answer_status - status: {status}")
                logger.info(f"SDK get_answer_status - has simulated_answer_percentages: {simulated_answer_percentages is not None}")
                
                # Serialize SDK response for JSON storage
                try:
                    serialized_data = serialize_sdk_response(result.data if hasattr(result, 'data') else result)
                    logger.info("Successfully serialized SDK response for get_answer_status")
                except Exception as serialization_error:
                    logger.error(f"Failed to serialize SDK response in get_answer_status: {serialization_error}")
                    # Fallback to basic info
                    serialized_data = {
                        "status": status,
                        "simulated_answer_percentages": simulated_answer_percentages,
                        "serialization_error": str(serialization_error)
                    }
                
                return {
                    "success": True,
                    "status": status,
                    "simulated_answer_percentages": simulated_answer_percentages,
                    "raw_data": serialized_data,
                    "errors": getattr(result, 'errors', [])
                }
            else:
                # HTTP fallback
                return self._get_answer_status_http(answer_id)
                
        except Exception as e:
            logger.error(f"Error getting answer status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_answer_status_http(self, answer_id: str) -> Dict:
        """HTTP fallback for getting answer status"""
        response = requests.get(
            f"{self.base_url}/v1/answers/{answer_id}",
            headers={"authorization": self.api_key},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        answer_data = data.get("data", {})
        
        return {
            "success": True,
            "status": answer_data.get("status"),
            "simulated_answer_percentages": answer_data.get("simulated_answer_percentages"),
            "raw_data": data,
            "errors": data.get("errors", [])
        }
    
    def poll_until_complete(self, answer_id: str, max_wait_seconds: int = 60) -> Dict:
        """
        Poll an answer until it's complete or timeout - following official SDK pattern
        Progression: Queued → Running → Predicted
        """
        start_time = time.time()
        
        while (time.time() - start_time) < max_wait_seconds:
            result = self.get_answer_status(answer_id)
            
            if not result["success"]:
                return result
            
            status = result["status"]
            
            # Status progression: Queued → Running → Predicted
            if status == "Predicted":
                return result
            elif status in ["Failed", "Error"]:
                return {
                    "success": False,
                    "error": f"Simulation failed with status: {status}",
                    "raw_data": result.get("raw_data")
                }
            
            # Wait before next poll - official SDK uses 1 second intervals
            time.sleep(1)
        
        return {
            "success": False,
            "error": "Timeout waiting for simulation to complete",
            "answer_id": answer_id
        }
    
    def simulate_and_poll(self, population_id: str, question: str, 
                         question_type: str, answer_options: Optional[List[str]] = None) -> Dict:
        """
        Convenience method following official SDK pattern:
        1. Simulate answer
        2. Poll until Predicted status
        """
        # First, verify the population exists (optional but good practice)
        pop_result = self.get_population(population_id)
        if not pop_result["success"]:
            logger.warning(f"Population {population_id} verification failed: {pop_result.get('error')}")
            # Continue anyway as population might still work for simulation
        
        # Start simulation
        sim_result = self.simulate_answer(population_id, question, question_type, answer_options)
        
        if not sim_result["success"]:
            return sim_result
        
        answer_id = sim_result["answer_id"]
        if not answer_id:
            return {
                "success": False,
                "error": "No answer ID returned from simulation",
                "raw_data": sim_result.get("data")
            }
        
        # Poll until complete - following the official SDK pattern
        if self.use_sdk:
            # If using SDK, we can implement the same polling logic as the official quickstart
            try:
                while True:
                    result = self.get_answer_status(answer_id)
                    if not result["success"]:
                        return result
                    
                    if result["status"] == "Predicted":
                        return result
                    elif result["status"] in ["Failed", "Error"]:
                        return {
                            "success": False,
                            "error": f"Simulation failed with status: {result['status']}",
                            "raw_data": result.get("raw_data")
                        }
                    
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                return {
                    "success": False,
                    "error": "Polling interrupted by user",
                    "answer_id": answer_id
                }
        else:
            # Use our polling method for HTTP fallback
            return self.poll_until_complete(answer_id)
    
    def test_population(self, population_id: str) -> Dict:
        """
        Trigger an accuracy test for a population model
        POST /v1/populations/{population_id}/test
        """
        try:
            if self.use_sdk:
                # SDK method if available
                try:
                    result = self.client.populations.test(population_id)
                    return {
                        "success": True,
                        "data": result.data if hasattr(result, 'data') else result,
                        "errors": getattr(result, 'errors', [])
                    }
                except AttributeError:
                    # Fallback to HTTP
                    return self._test_population_http(population_id)
            else:
                return self._test_population_http(population_id)
                
        except Exception as e:
            logger.error(f"Error testing population {population_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _test_population_http(self, population_id: str) -> Dict:
        """HTTP fallback for population testing"""
        response = requests.post(
            f"{self.base_url}/v1/populations/{population_id}/test",
            headers={"authorization": self.api_key},
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        return {
            "success": True,
            "data": data.get("data", {}),
            "errors": data.get("errors", [])
        }
