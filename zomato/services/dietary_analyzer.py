from typing import List, Dict
import re

class DietaryAnalyzer:
    def __init__(self):
        self.restriction_patterns = {
            'dairy': r'paneer|cheese|cream|butter|milk|ghee|curd|yogurt|lassi|kheer',
            'gluten': r'bread|naan|roti|paratha|pasta|pizza|wheat|maida',
            'nuts': r'cashew|almond|peanut|walnut|pistachio|hazelnut',
            'diabetes': r'sweet|dessert|cake|ice cream|sugar|gulab jamun|jalebi|kheer|mithai',
            'hypertension': r'pickle|papad|chips|fries|salted|salty|fried',
            'vegan': r'paneer|cheese|egg|chicken|mutton|fish|butter|ghee|cream|milk|curd',
            'keto': r'rice|potato|bread|naan|roti|sweet|paratha',
            'shellfish': r'prawn|shrimp|crab|lobster|oyster|clam',
            'eggs': r'egg|omelette|scrambled|boiled egg',
            'soy': r'soy|tofu|soya'
        }
        
        self.carb_foods = r'rice|potato|bread|naan|roti|pasta'
        self.healthy_prep = r'salad|grilled|steamed|boiled|baked'
        self.unhealthy_prep = r'fried|deep fried|butter|creamy|rich'
    
    def analyze_item(self, item_name: str, restrictions: List[str]) -> Dict:
        """
        Analyze a menu item against dietary restrictions
        Returns: {score: int, notes: str}
        """
        name = item_name.lower()
        score = 10
        warnings = []
        notes = []
        
        # Check each restriction
        for restriction in restrictions:
            restriction_key = restriction.lower().strip()
            
            # Dairy checks
            if 'dairy' in restriction_key or 'lactose' in restriction_key:
                if re.search(self.restriction_patterns['dairy'], name):
                    score -= 6
                    warnings.append("Contains dairy products")
            
            # Gluten checks
            if 'gluten' in restriction_key:
                if re.search(self.restriction_patterns['gluten'], name):
                    score -= 6
                    warnings.append("Contains gluten")
            
            # Nut checks
            if 'nut' in restriction_key:
                if re.search(self.restriction_patterns['nuts'], name):
                    score -= 7
                    warnings.append("Contains nuts - allergy risk")
            
            # Diabetes checks
            if 'diabet' in restriction_key:
                if re.search(self.restriction_patterns['diabetes'], name):
                    score -= 5
                    warnings.append("High sugar content - not suitable for diabetes")
                if re.search(self.carb_foods, name):
                    score -= 2
                    warnings.append("High carbohydrate content")
            
            # Hypertension/Sodium checks
            if 'hypertension' in restriction_key or 'sodium' in restriction_key:
                if re.search(self.restriction_patterns['hypertension'], name):
                    score -= 5
                    warnings.append("High sodium content")
            
            # Vegan checks
            if 'vegan' in restriction_key:
                if re.search(self.restriction_patterns['vegan'], name):
                    score -= 7
                    warnings.append("Contains animal products")
                else:
                    notes.append("Vegan-friendly option")
            
            # Vegetarian checks
            if 'vegetarian' in restriction_key:
                if re.search(r'chicken|mutton|fish|meat|prawn|egg', name):
                    score -= 7
                    warnings.append("Contains meat/eggs")
            
            # Keto checks
            if 'keto' in restriction_key:
                if re.search(self.restriction_patterns['keto'], name):
                    score -= 5
                    warnings.append("High carb - not keto-friendly")
            
            # Shellfish checks
            if 'shellfish' in restriction_key:
                if re.search(self.restriction_patterns['shellfish'], name):
                    score -= 8
                    warnings.append("Contains shellfish - allergy risk")
            
            # Egg checks
            if 'egg' in restriction_key:
                if re.search(self.restriction_patterns['eggs'], name):
                    score -= 6
                    warnings.append("Contains eggs")
            
            # Soy checks
            if 'soy' in restriction_key:
                if re.search(self.restriction_patterns['soy'], name):
                    score -= 5
                    warnings.append("Contains soy")
        
        # Positive indicators
        if re.search(self.healthy_prep, name):
            notes.append("Healthy preparation method")
            score = min(10, score + 1)
        
        # Negative indicators
        if re.search(self.unhealthy_prep, name):
            notes.append("High-fat preparation method")
            score -= 1
        
        # Default safe message
        if not warnings:
            notes.append("Appears safe for your dietary restrictions")
        
        return {
            "score": max(0, min(10, score)),
            "notes": ". ".join(warnings + notes)
        }
    
    def get_recommendation(self, score: int) -> str:
        """
        Get recommendation based on safety score
        """
        if score >= 8:
            return "Highly Recommended"
        elif score >= 5:
            return "Consume with Caution"
        else:
            return "Not Recommended"