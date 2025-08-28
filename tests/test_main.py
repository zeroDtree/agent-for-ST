import unittest
from unittest.mock import patch, MagicMock
from main import create_graph, chatbot_route
from states.state import State
from langchain_core.messages import AIMessage

class TestMain(unittest.TestCase):
    
    def test_create_graph(self):
        """测试图创建函数"""
        graph = create_graph()
        self.assertIsNotNone(graph)
        self.assertTrue(hasattr(graph, 'stream'))
    
    @patch('main.cached_is_safe_command')
    def test_chatbot_route_whitelist(self, mock_is_safe):
        """测试白名单路由"""
        mock_is_safe.return_value = True
        
        # 模拟shel命令调用
        ai_message = AIMessage(
            content="",
            tool_calls=[{
                "name": "run_shell_command_popen_tool",
                "args": {"command": "ls -la"}
            }]
        )
        
        state = {"messages": [ai_message]}
        result = chatbot_route(state)
        self.assertEqual(result, "my_tools")
    
    @patch('main.cached_is_safe_command')
    def test_chatbot_route_non_whitelist(self, mock_is_safe):
        """测试非白名单路由"""
        mock_is_safe.return_value = False
        
        ai_message = AIMessage(
            content="",
            tool_calls=[{
                "name": "run_shell_command_popen_tool", 
                "args": {"command": "rm -rf /"}
            }]
        )
        
        state = {"messages": [ai_message]}
        result = chatbot_route(state)
        self.assertEqual(result, "human_confirm")

if __name__ == "__main__":
    unittest.main()
