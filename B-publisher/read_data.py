import json
# from datetime import datetime

def read_file(path,topic):
    results=[]
    with open(path, 'r') as file:
        for line in file:
            data = json.loads(line)
            for key, value in data.items():
                result={
                    "topic": topic,
                    "payload": {
                        "ts": key,
                        "value": value
                    }
                }
                results.append(result)
    results.sort(key=lambda r: r["payload"]["ts"])
    return results

if __name__ == "__main__":
    input_dict={
        'env/temperature': 'B-publisher/data/temperature.txt',
        'env/humidity': 'B-publisher/data/humidity.txt',
        'env/pressure': 'B-publisher/data/pressure.txt'
    }
    for key, path in input_dict.items():
        data=read_file(path,key)
        # TODO: send data to MQTT broker
        for item in data:
            print(item)
