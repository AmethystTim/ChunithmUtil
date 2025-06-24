import time
import os

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs')

class AliasLogger:
    def __init__(self):
        pass
    
    def log(self, info: dict):
        '''记录添加别名行为
        
        Args:
            info (dict): {用户QQ号, 用户昵称, 所在群号, 添加歌曲cid, 添加歌曲名称, 添加歌曲有效别名, 添加歌曲无效别名}
        '''
        pass
        current_date = time.strftime('%Y-%m-%d', time.localtime())
        log_file_path = os.path.join(LOG_DIR, f'{current_date}.log')
        if not os.path.exists(log_file_path):
            with open(log_file_path, 'w', encoding='utf-8') as f:
                f.write(f"{time.strftime('%Y-%m-%d', time.localtime())} 别名添加记录\n")
        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\t群{info['group_id']} 用户{info['user_name']}({info['user_id']}) 为 {info['cid']} - {info['songId']} 添加有效别名 {info['valid_aliases']} 无效别名{info['invalid_aliases']}\n")