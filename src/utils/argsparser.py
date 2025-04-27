import re
def parseArgs(regex: str, text: str) -> list:
    '''捕获参数
    
    Args:
        regex (str): 正则表达式
        text (str): 指令内容
    Returns:
        list: 捕获到的参数列表
    '''
    match = re.search(regex, text)
    return list(match.groups()) if match else []