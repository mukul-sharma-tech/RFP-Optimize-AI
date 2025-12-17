import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Gemini
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("WARNING: GOOGLE_API_KEY not found. Ensure .env is set.")
else:
    genai.configure(api_key=api_key)

MODEL_NAME = "gemini-2.5-flash"

def load_repository_file(filename):
    """Helper to read the external text files."""
    try:
        with open(filename, "r") as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: {filename} not found. Please ensure Admin has uploaded it."

class AgentOrchestrator:
    def __init__(self):
        self._model = None
        self._tech_agent = None
        self._pricing_agent = None

    @property
    def model(self):
        if self._model is None:
            self._model = genai.GenerativeModel(MODEL_NAME)
        return self._model

    @property
    def tech_agent(self):
        if self._tech_agent is None:
            self._tech_agent = TechnicalAgent(self.model)
        return self._tech_agent

    @property
    def pricing_agent(self):
        if self._pricing_agent is None:
            self._pricing_agent = PricingAgent(self.model)
        return self._pricing_agent

    def run_analysis(self, rfp_data: dict, check_constraints: bool = True) -> dict:
        print(f"AI Orchestrator: Analyzing RFP '{rfp_data.get('title')}' using Gemini AI...")

        # Check constraints if enabled
        if check_constraints:
            constraint_check = self.check_qualification_constraints(rfp_data)
            if not constraint_check["qualified"]:
                return {
                    "spec_match_score": 0,
                    "win_probability": 0,
                    "extracted_specs": {},
                    "financial_analysis": {},
                    "recommendation": "REJECT - Does not meet qualification criteria",
                    "recommendation_reason": constraint_check["reason"],
                    "suggestions": ["Review qualification criteria with admin", "Consider adjusting RFP requirements"],
                    "agent_status": "completed"
                }

        # Combine title and description for analysis
        rfp_text = f"Title: {rfp_data.get('title', '')}\nDescription: {rfp_data.get('description', '')}"

        try:
            # Run technical analysis
            tech_result = self.tech_agent.analyze_specs(rfp_text)

            # Run pricing analysis
            pricing_result = self.pricing_agent.calculate_costs(
                tech_result.get("matched_skus", []),
                tech_result.get("standardized_specs", {})
            )

            # Calculate win probability
            spec_match_score = tech_result.get("spec_match_score", 0)
            margin = pricing_result.get("margin", 20)
            win_probability = self.calculate_win_probability(spec_match_score, margin)

            # Determine recommendation
            if win_probability >= 70 and spec_match_score >= 75:
                recommendation = "SELECT - High confidence recommendation"
                recommendation_reason = "Excellent match with strong win probability and high specification alignment."
            elif win_probability >= 50 and spec_match_score >= 60:
                recommendation = "CONSIDER - Moderate confidence"
                recommendation_reason = "Good potential with reasonable win probability and acceptable specification match."
            elif win_probability >= 30:
                recommendation = "REVIEW - Low confidence"
                recommendation_reason = "Marginal win probability, requires careful evaluation of competition and pricing."
            else:
                recommendation = "REJECT - Not recommended"
                recommendation_reason = "Low win probability and poor specification match suggest pursuing other opportunities."

            # Generate suggestions
            suggestions = []
            if spec_match_score < 70:
                suggestions.append("Consider adjusting technical specifications to better match available product portfolio")
            if win_probability < 60:
                suggestions.append("Review pricing strategy - current margin may be too aggressive for market conditions")
            if len(suggestions) == 0:
                suggestions.append("Proposal appears well-aligned with requirements - focus on competitive pricing and delivery timeline")

            return {
                "spec_match_score": spec_match_score,
                "extracted_specs": tech_result.get("standardized_specs", {}),
                "matched_skus": tech_result.get("matched_skus", []),
                "financial_analysis": pricing_result,
                "win_probability": win_probability,
                "recommendation": recommendation,
                "recommendation_reason": recommendation_reason,
                "suggestions": suggestions,
                "agent_status": "completed"
            }

        except Exception as e:
            print(f"AI Analysis Error: {e}")
            # Fallback to mock data if AI fails
            return {
                "spec_match_score": 50.0,
                "win_probability": 45.0,
                "extracted_specs": {
                    "product_type": "Analysis Failed",
                    "voltage_rating": "Analysis Failed",
                    "material": "Analysis Failed",
                    "durability_rating": "Analysis Failed",
                    "compliance_standards": "Analysis Failed"
                },
                "financial_analysis": {
                    "breakdown": {"material_cost": 0, "service_fees": 0, "applied_fees_list": []},
                    "total_cost_internal": 0,
                    "total_bid_value": 0,
                    "margin": 20.0,
                    "currency": "USD"
                },
                "recommendation": "REVIEW - Low confidence",
                "recommendation_reason": "AI analysis failed, using fallback values. Manual review recommended.",
                "suggestions": ["Re-run AI analysis when service is available", "Manually review RFP requirements against company capabilities"],
                "agent_status": "completed"
            }

    def check_qualification_constraints(self, rfp_data: dict) -> dict:
        """Check if RFP meets qualification constraints"""
        try:
            # This would normally query the database for active qualification rules
            # For now, return a mock check - in production, this would query MongoDB
            budget = rfp_data.get("budget", 0)

            # Relaxed mock constraint check - only reject if budget is 0 or negative
            if budget <= 0:
                return {
                    "qualified": False,
                    "reason": "Budget not specified or invalid"
                }

            return {"qualified": True, "reason": "Meets all qualification criteria"}

        except Exception as e:
            print(f"Error checking constraints: {e}")
            return {"qualified": True, "reason": "Constraint check failed, proceeding with analysis"}

    def calculate_win_probability(self, match_score, margin):
        # Heuristic: High Match + Good Margin = High Win Prob
        base_prob = match_score * 0.7
        if margin > 18:
            base_prob += 15
        elif margin < 10:
            base_prob -= 10
        # Ensure win probability is between 0 and 100
        return max(0, min(round(base_prob, 2), 100.0))

class TechnicalAgent:
    def __init__(self, model):
        self.model = model
        self.sku_data = load_repository_file("sku_repository.txt")

    def analyze_specs(self, rfp_text: str) -> dict:
        """
        Extracts RFP attributes specifically mapping them to the Admin Repository fields.
        """
        prompt = f"""
        You are an expert Industrial Technical Engineer.
        
        OBJECTIVE: 
        Map the Client's RFP requirements to our Internal Data Schema.
        
        --- INTERNAL ADMIN DATA SCHEMA (Our Attributes) ---
        1. product_type (e.g., Widget, Cable, Gadget)
        2. voltage_rating (e.g., 415V, 11kV)
        3. material (e.g., Steel, Copper, XLPE)
        4. durability_rating (e.g., Medium, High, IP67)
        5. compliance_standards (e.g., ISO 9001, IEC 60502)
        
        --- INTERNAL PRODUCT REPOSITORY (Reference Data) ---
        {self.sku_data}
        ----------------------------------------------------

        --- CLIENT RFP TEXT ---
        {rfp_text}
        -----------------------

        INSTRUCTIONS:
        1. Read the Client RFP.
        2. Extract values for the 5 Schema Attributes listed above. If not specified, use "Not Specified".
        3. Compare these extracted values against the Repository to find the best matching SKU IDs.
        4. Calculate a match score (0-100) based on how well the extracted specs match the repository SKUs. Consider exact matches, partial matches, and compatibility. For example, if voltage_rating matches exactly and compliance_standards overlap, give high score.

        OUTPUT FORMAT (Raw JSON Only):
        {{
            "standardized_specs": {{
                "product_type": "...",
                "voltage_rating": "...",
                "material": "...",
                "durability_rating": "...",
                "compliance_standards": "..."
            }},
            "matched_skus": ["P00X", "P00Y"],
            "spec_match_score": 85.5,
            "match_reasoning": "Brief explanation of why these SKUs fit."
        }}
        """

        try:
            response = self.model.generate_content(prompt)
            # Sanitization to handle potential markdown formatting from LLM
            cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned_text)
        except Exception as e:
            print(f"Technical Agent Error: {e}")
            return {
                "spec_match_score": 0, 
                "standardized_specs": {
                    "product_type": "Error", "voltage_rating": "Error", 
                    "material": "Error", "durability_rating": "Error", "compliance_standards": "Error"
                }, 
                "matched_skus": []
            }

class PricingAgent:
    def __init__(self, model):
        self.model = model
        self.pricing_data = load_repository_file("pricing_repository.txt")

    def calculate_costs(self, matched_skus: list, specs: dict) -> dict:
        prompt = f"""
        You are a Senior Pricing Analyst.
        
        TASK: Generate a commercial bid based on our Admin Pricing Rules.
        
        --- ADMIN PRICING REPOSITORY ---
        {self.pricing_data}
        --------------------------------

        INPUTS:
        - Target SKUs: {matched_skus}
        - Client Specs: {specs}

        INSTRUCTIONS:
        1. Lookup Base Price for each SKU in the repository.
        2. Apply 'Service Fees' if the Specs imply testing (e.g., if 'compliance_standards' mentions IEC, add IEC fees).
        3. Calculate a Final Bid with a 20% margin.

        OUTPUT FORMAT (Raw JSON Only):
        {{
            "breakdown": {{
                "material_cost": <float>,
                "service_fees": <float>,
                "applied_fees_list": ["Fee Name 1", "Fee Name 2"]
            }},
            "total_cost_internal": <float>,
            "total_bid_value": <float>,
            "margin": <float percent>,
            "currency": "USD"
        }}
        """

        try:
            response = self.model.generate_content(prompt)
            cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(cleaned_text)
        except Exception as e:
            print(f"Pricing Agent Error: {e}")
            return {"margin": 0, "total_bid_value": 0}

orchestrator = AgentOrchestrator()