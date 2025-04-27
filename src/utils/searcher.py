import difflib
import json

class Searcher:
    def __init__(self):
        pass
    
    def generalFuzzySearch(self, query: str, searchlist: list) -> list:
        '''
        通用模糊搜索，返回匹配结果列表
        
        args:
            query: 搜索关键字
            searchlist: 待搜索列表
        return:
            匹配结果列表
        '''
        if None in searchlist:
            searchlist.remove(None)
        
        # 1. 精准匹配
        lowercase_searchlist = [item.lower() for item in searchlist]
        if query.lower() in lowercase_searchlist:
            return [searchlist[lowercase_searchlist.index(query.lower())]]
        
        # 2.1 模糊搜索
        results = difflib.get_close_matches(query.lower(), lowercase_searchlist, n=10, cutoff=0.8)
        results = [searchlist[lowercase_searchlist.index(result)] for result in results]
        
        # 2.2 子串匹配
        for item in searchlist:
            if query.lower() in item.lower():
                results.append(item)
        
        results = list(set(results))
        return results
