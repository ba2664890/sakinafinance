from django.test import TestCase
from unittest.mock import patch, MagicMock
from sakinafinance.ai_engine.services import AIService

class AIServiceTest(TestCase):
    def setUp(self):
        self.ai_service = AIService()
        self.sample_data = {
            'total_liquidity': 15000000,
            'net_cashflow_30d': 2000000,
            'dso_days': 40,
            'dio_days': 30,
            'dpo_days': 45,
            'cash_cycle_days': 25
        }

    @patch('openai.OpenAI')
    def test_generate_treasury_insights_real(self, mock_openai):
        # Mock OpenAI response
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Insight réel de l'IA test."))]
        mock_client.chat.completions.create.return_value = mock_response

        # Re-init service with mocked client
        self.ai_service.client = mock_client
        
        insight = self.ai_service.generate_treasury_insights(self.sample_data)
        self.assertEqual(insight, "Insight réel de l'IA test.")
        mock_client.chat.completions.create.assert_called_once()

    def test_generate_treasury_insights_simulated(self):
        # Force simulation by removing client
        self.ai_service.client = None
        insight = self.ai_service.generate_treasury_insights(self.sample_data)
        
        self.assertIn("excédent de liquidité", insight)
        self.assertIn("text-primary fw-bold", insight)
