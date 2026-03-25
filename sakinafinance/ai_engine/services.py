import openai
from django.conf import settings
import logging

logger = logging.getLogger('sakinafinance')

class AIService:
    """
    Service to interact with AI Models (OpenAI/Gemini) for SakinaFinance.
    """
    def __init__(self):
        self.api_key = getattr(settings, 'OPENAI_API_KEY', None)
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None
            logger.warning("OPENAI_API_KEY not found in settings. AI features will be simulated.")

    def generate_treasury_insights(self, data):
        """
        Generate financial insights from treasury data.
        data format: {
            'total_liquidity': float,
            'net_cashflow_30d': float,
            'dso_days': int,
            'dio_days': int,
            'dpo_days': int,
            'cash_cycle_days': int
        }
        """
        if not self.client:
            return self._get_simulated_insights(data)

        prompt = f"""
        En tant qu'expert en finance d'entreprise (CFO), analyse les indicateurs de trésorerie suivants pour une entreprise :
        - Liquidité totale : {data.get('total_liquidity'):,.0f} XOF
        - Flux de trésorerie net (30j) : {data.get('net_cashflow_30d'):,.0f} XOF
        - DSO (Délai Client) : {data.get('dso_days')} jours
        - DIO (Délai Stock) : {data.get('dio_days')} jours
        - DPO (Délai Fournisseur) : {data.get('dpo_days')} jours
        - Cycle de conversion du cash (CCC) : {data.get('cash_cycle_days')} jours

        Fournis une recommandation stratégique courte (max 3 phrases) en français, riche en vocabulaire financier.
        La réponse doit être au format HTML léger (avec spans pour les valeurs clés).
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo", # Use 4-turbo or 4o if available, gpt-3.5-turbo for speed/cost
                messages=[
                    {"role": "system", "content": "Tu es un conseiller financier IA expert."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"AI Insight error: {str(e)}")
            return self._get_simulated_insights(data)

    def _get_simulated_insights(self, data):
        """Fallback for when API is unavailable or limits reached."""
        if data.get('total_liquidity', 0) > 0:
            return """
                L'analyse indique un <span class="text-primary fw-bold">excédent de liquidité</span>. 
                Optimisez votre <span class="text-white fw-bold">Cycle de Conversion du Cash</span> 
                en plaçant vos surplus sur un compte à terme ou en renégociant les escomptes fournisseurs.
            """
        return "Analyse des cycles en cours... L'IA calcule la stratégie optimale."
