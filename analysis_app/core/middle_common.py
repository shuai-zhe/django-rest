import copy

worlds = ["沙雕", "测试中"]
# 将所有的关键字预处理变成树结构
# 每一个字符都是一个节点，而下一个节点是上一个节点的子节点
# {"福":{"音":{"会"}}}


class DFA:
    def __init__(self):
        self.__worlds_dfa_dict = {}

    def set_world_node(self, text, fnode=[]):
        node_dict = self.__worlds_dfa_dict
        for node in fnode:
            node_dict = node_dict[node]

        if not node_dict.get(text[0]):
            node_dict.update({text[0]: {}})

        if len(text) == 1:
            return
        # 继续下一次操作
        self.set_world_node(text=text[1:], fnode=fnode + [text[0]])

    def get_texts(self, text: list = None):
        # 获取违禁词方式
        return worlds

    def set_worlds_dfa(cls):
        # 设置所有的词节点  可以考虑定时更新词组
        [cls.set_world_node(world) for world in cls.get_texts()]
        return cls

    @property
    def get_worlds_dfa(self):
        # 返回树;可以考虑定期重新刷新获取最新数据；当然也可以通过数据库方式定时加载
        self.set_worlds_dfa()
        return self.__worlds_dfa_dict

    def predict(self, text):
        # 匹配是否 违禁词
        char_dict = self.get_worlds_dfa
        for char in text:
            char_dict = char_dict.get(char, {})

        return not bool(char_dict)


_DFA = DFA()
