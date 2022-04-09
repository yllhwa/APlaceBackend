from flask import Flask, make_response, send_file
from flask_socketio import SocketIO, emit
from flask_redis import FlaskRedis
from config import SECRET_KEY, REDIS_URL, MAP_SIZE
from PIL import Image
import numpy as np
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['REDIS_URL'] = REDIS_URL

# websocket
socketio = SocketIO(app, cors_allowed_origins="*")

# redis
redis_client = FlaskRedis()
redis_client.init_app(app)


@app.route('/api/current_map', methods=['GET'])
def get_current_map():
    # get bmp image from bitmap
    bitmap = redis_client.execute_command('get', 'bitmap')
    bitmap = np.frombuffer(bitmap, dtype=np.uint8)
    bitmap = bitmap.reshape(1000, 1000, 4)
    bitmap = Image.fromarray(bitmap)
    res_data = io.BytesIO()
    bitmap.save(res_data, "bmp")
    res_data.seek(0)
    return send_file(res_data, mimetype='image/bmp')


@socketio.on('draw', namespace='/draw')
def draw(json):
    # draw a pixel to bitmap
    x = json['x']
    y = json['y']
    color = json['color']
    if x < 0 or x >= MAP_SIZE['width'] or y < 0 or y >= MAP_SIZE['height']:
        return
    set_bitmap(x, y, color)
    emit('draw_operation', json, broadcast=True)


def init_bitmap():
    # init a 1000*1000 bitmap
    redis_client.execute_command(
        'set', 'bitmap', b'\x00\x00\x00\x00'*1000*1000)


def set_bitmap(x, y, value):
    # use bitfield to set a pixel
    return redis_client.execute_command('bitfield', 'bitmap', 'set', 'u32', (x+y*1000)*32, value)


# 判断redis是否存在bitmap
if redis_client.get('bitmap') is None:
    init_bitmap()
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
