import unittest
from unittest.mock import patch, MagicMock
from main import main
from utils.logger import log_command_execution
from utils.cache import cached_is_safe_command

class TestIntegration(unittest.TestCase):
    
    @patch('builtins.input')
    @patch('main.graph')
    @patch('main.llm_with_tools')
    def test_basic_workflow(self, mock_llm, mock_graph, mock_input):
        """测试基本工作流"""
        mock_input.side_effect = ["hello", KeyboardInterrupt]
        
        # 模拟LLM响应
        mock_response = MagicMock()
        mock_response.content = "Hello! How can I help you?"
        mock_llm.invoke.return_value = mock_response
        
        # 模拟图执行
        mock_graph.stream.return_value = [{"messages": [mock_response]}]
        
        # 运行主程序（应该退出循环）
        with self.assertRaises(SystemExit):
            main()
    
    def test_log_command_execution(self):
        """测试命令执行日志"""
        # 这个测试会创建日志文件，但是可以测试函数调用
        try:
            log_command_execution("ls -la", "test", "success", "file1.txt\nfile2.txt")
            self.assertTrue(True)  # 如果没有抛出异常，就说明成功
        except Exception as e:
            self.fail(f"log_command_execution failed: {e}")
    
    def test_cached_is_safe_command(self):
        """测试缓存函数"""
        # 第一次调用应该调用原函数
        result1 = cached_is_safe_command("ls")
        
        # 第二次调用同样的命令应该使用缓存
        result2 = cached_is_safe_command("ls")
        
        self.assertEqual(result1, result2)

if __name__ == "__main__":
    unittest.main()
