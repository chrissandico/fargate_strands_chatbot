import requests
import json
import sys

def test_weather_streaming(location):
    """
    Test the weather streaming endpoint with the given location.
    
    Args:
        location (str): The location to get weather information for
    """
    url = "http://AgentF-Agent-fd2EkmoQbY5h-216549744.us-east-1.elb.amazonaws.com/weather-streaming"
    prompt = f"What is the weather like in {location} today?"
    payload = {"prompt": prompt}
    headers = {"Content-Type": "application/json"}
    
    print(f"Sending request for weather in {location}...")
    print(f"Prompt: '{prompt}'")
    print("Streaming response:\n")
    
    try:
        with requests.post(url, data=json.dumps(payload), headers=headers, stream=True) as response:
            if response.status_code != 200:
                print(f"Error: Received status code {response.status_code}")
                print(response.text)
                return
                
            for chunk in response.iter_content(chunk_size=None):
                if chunk:
                    print(chunk.decode('utf-8'), end='', flush=True)
    except requests.exceptions.RequestException as e:
        print(f"Error making request: {e}")

if __name__ == "__main__":
    # Use command line argument for location or default to "Seattle"
    location = sys.argv[1] if len(sys.argv) > 1 else "Seattle"
    test_weather_streaming(location)
