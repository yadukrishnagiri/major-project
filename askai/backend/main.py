import pdfplumber
import json
from typing import Dict, List, Optional
import logging
import google.generativeai as genai
from dotenv import load_dotenv
import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Add these after app initialization
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Add secret key for JWT
app.config['JWT_SECRET_KEY'] = 'your-secret-key-here'  # Change this to a secure secret key
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 86400  # 24 hours

class CVAnalyzer:
    def __init__(self):
        """Initialize CV analyzer with Gemini API"""
        load_dotenv()
        self.job_profile = None
        
        # Configure Gemini
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-pro')
        self.cv_context = None
        self.timeout = 300  # 5 minutes timeout
        self.executor = ThreadPoolExecutor(max_workers=1)

    def extract_text_from_pdf(self, pdf_path: str) -> Optional[str]:
        """Extract text from PDF file"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    text += page.extract_text() or ""
                return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return None

    def analyze_cv(self, cv_text: str) -> Dict:
        """Analyze CV using Gemini AI with timeout"""
        logger.info("\nAnalyzing CV...")
        
        prompt = f"""
        You are a professional CV analyzer. Analyze this CV and return ONLY a JSON object with no additional text.
        The JSON must follow this exact structure:
        {{
            "technical_skills": {{"skill_name": "level(1-5)"}},
            "years_experience": "number",
            "key_achievements": ["list", "of", "achievements"],
            "areas_for_improvement": ["list", "of", "suggestions"],
            "potential_questions": ["list", "of", "relevant", "interview", "questions"]
        }}

        Make sure:
        1. Response is valid JSON
        2. No markdown formatting or code blocks
        3. Skills are rated 1-5
        4. Achievements are complete sentences
        5. Questions are relevant for {self.job_profile} position

        CV Content:
        {cv_text}
        """

        try:
            # Run analysis with timeout
            future = self.executor.submit(self._get_analysis, prompt)
            response = future.result(timeout=self.timeout)
            
            # Clean and parse response
            text = self._clean_response(response.text)
            self.cv_context = json.loads(text)
            return self.cv_context
            
        except TimeoutError:
            logger.error(f"Analysis timed out after {self.timeout} seconds")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {response.text if 'response' in locals() else 'No response'}")
            return {}
        except Exception as e:
            logger.error(f"Analysis failed: {str(e)}")
            return {}
        finally:
            # Cleanup
            try:
                self.executor.shutdown(wait=False)
                self.executor = ThreadPoolExecutor(max_workers=1)
            except:
                pass

    def _get_analysis(self, prompt: str):
        """Helper method to get analysis from Gemini"""
        return self.model.generate_content(prompt)

    def _clean_response(self, text: str) -> str:
        """Clean the response text"""
        text = text.strip()
        if text.startswith("```") and text.endswith("```"):
            text = text[text.find("{"):text.rfind("}")+1]
        elif text.startswith("`") and text.endswith("`"):
            text = text[1:-1]
        return text

    def print_analysis(self, analysis: Dict):
        """Print formatted analysis results"""
        if not analysis:
            logger.error("No analysis data available")
            return
            
        print("\nCV Analysis Results")
        print("=" * 60)
        
        if "technical_skills" in analysis:
            print("\nTechnical Skills:")
            for skill, level in analysis["technical_skills"].items():
                stars = "★" * int(level) + "☆" * (5 - int(level))
                print(f"  • {skill:<20} {stars}")
        
        if "years_experience" in analysis:
            print(f"\nYears of Experience: {analysis['years_experience']}")
        
        if "key_achievements" in analysis:
            print("\nKey Achievements:")
            for achievement in analysis["key_achievements"]:
                print(f"  • {achievement}")
        
        if "areas_for_improvement" in analysis:
            print("\nAreas for Improvement:")
            for area in analysis["areas_for_improvement"]:
                print(f"  • {area}")
        
        print("\n" + "=" * 60)

    def get_interview_questions(self) -> List[Dict[str, str]]:
        """Get interview questions based on CV analysis"""
        if not self.cv_context or "potential_questions" not in self.cv_context:
            return []
            
        questions = []
        for q in self.cv_context["potential_questions"]:
            questions.append({
                "question": q,
                "category": "technical",
                "keywords": [word.lower() for word in q.split() if len(word) > 3]
            })
        return questions

class InteractiveInterviewer:
    def __init__(self):
        """Initialize Interactive Interviewer with Gemini API"""
        load_dotenv()
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-pro')
        self.cv_context = None
        self.interview_results = {
            "candidate_name": "",
            "position": "",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "technical_skills": {},
            "questions": [],
            "overall_score": 0,
            "feedback": ""
        }
        self.max_questions = 10  # Maximum number of questions
        self.difficulty_levels = ["basic", "intermediate", "advanced"]
        self.current_difficulty = "basic"
        self.is_interview_complete = False  # New flag to track interview completion
        
        # Add new attributes
        self.question_bank = []
        self.current_question_index = 0
        self.questionsAsked = 0  # Track number of questions asked
    
    def generate_question_bank(self, cv_analysis: Dict) -> List[Dict]:
        """Generate a structured bank of interview questions based on CV analysis"""
        prompt = f"""
        Create 10 technical interview questions based on this CV analysis:
        {json.dumps(cv_analysis)}
        
        Requirements:
        1. 7 questions about projects and experience from CV
        2. 2 questions about technical skills mentioned
        3. 1 critical thinking question unrelated to CV
        
        Return a JSON array with this structure:
        [{{
            "question": "question_text",
            "type": "project|technical|critical",
            "difficulty": "basic|intermediate",
            "focus_area": "specific_skill_or_project",
            "follow_up_hints": ["possible_follow_up_questions"]
        }}]
        
        Ensure questions progress from basic to intermediate difficulty.
        """
        
        try:
            response = self.model.generate_content(prompt)
            questions = json.loads(self._clean_response(response.text))
            self.question_bank = questions
            return questions
        except Exception as e:
            logger.error(f"Failed to generate question bank: {str(e)}")
            return []

    def get_next_question(self) -> Optional[Dict]:
        """Get the next question from the question bank"""
        if self.current_question_index < len(self.question_bank):
            question = self.question_bank[self.current_question_index]
            self.current_question_index += 1
            return question
        return None

    def evaluate_answer(self, question: str, answer: str, context: Dict) -> Dict:
        """Evaluate candidate's answer using Gemini"""
        # Check for end command
        if answer.lower().strip() in ['end', 'quit', 'stop', 'exit']:
            self.is_interview_complete = True
            return {
                "score": 0,
                "feedback": "Interview ended by candidate.",
                "technical_accuracy": 0,
                "communication": 0,
                "interview_complete": True
            }

        # Check question limit
        if self.questionsAsked >= self.max_questions:
            self.is_interview_complete = True
            return {
                "score": 0,
                "feedback": "Maximum number of questions reached.",
                "technical_accuracy": 0,
                "communication": 0,
                "interview_complete": True
            }

        # Handle very short or "idk" responses
        if len(answer.strip()) < 5 or answer.lower() in ['idk', 'i dont know', 'i do not know']:
            return {
                "score": 1,
                "feedback": "The answer shows lack of knowledge or effort. Consider providing more detailed responses.",
                "technical_accuracy": 1,
                "communication": 1,
                "suggested_followup": "Let's try a different topic. " + self._get_simpler_question(context),
                "adjust_difficulty": "easier",
                "topic_to_explore": "basics"
            }

        prompt = f"""
        As a technical interviewer for a {self.interview_results['position']} position, evaluate this answer.
        
        Question: {question}
        Candidate's Answer: {answer}
        Current Difficulty Level: {self.current_difficulty}
        
        Context from CV: {json.dumps(context)}
        
        Provide evaluation in this JSON format:
        {{
            "score": <number_between_1_and_10>,
            "feedback": "detailed_feedback",
            "technical_accuracy": <number_between_1_and_10>,
            "communication": <number_between_1_and_10>,
            "suggested_followup": "next_question_focusing_on_projects_and_technical_depth",
            "adjust_difficulty": "easier/harder/maintain",
            "topic_to_explore": "specific_technical_area_to_probe"
        }}
        """
        
        try:
            response = self.model.generate_content(prompt)
            evaluation = json.loads(self._clean_response(response.text))
            
            # Ensure numeric scores
            evaluation["score"] = float(str(evaluation["score"]).split()[0])
            evaluation["technical_accuracy"] = float(str(evaluation["technical_accuracy"]).split()[0])
            evaluation["communication"] = float(str(evaluation["communication"]).split()[0])
            
            # Adjust difficulty based on performance
            if evaluation.get("adjust_difficulty") == "harder" and self.current_difficulty != "advanced":
                self.current_difficulty = self.difficulty_levels[
                    min(self.difficulty_levels.index(self.current_difficulty) + 1, 2)
                ]
            elif evaluation.get("adjust_difficulty") == "easier" and self.current_difficulty != "basic":
                self.current_difficulty = self.difficulty_levels[
                    max(self.difficulty_levels.index(self.current_difficulty) - 1, 0)
                ]
                
            return evaluation
        except Exception as e:
            logger.error(f"Evaluation failed: {str(e)}")
            return self._default_evaluation()

    def _get_simpler_question(self, context: Dict) -> str:
        """Generate a simpler question when candidate struggles"""
        try:
            skills = list(context.get("technical_skills", {}).keys())
            if skills:
                return f"Could you explain your experience with {skills[0]}?"
            return "Could you tell me about your technical background?"
        except:
            return "Could you tell me about your technical background?"

    def _get_project_based_question(self, cv_analysis: Dict, previous_answers: List[Dict]) -> str:
        """Generate a project-focused question based on CV and previous answers"""
        prompt = f"""
        Generate a detailed technical question about the candidate's projects.
        
        CV Context: {json.dumps(cv_analysis)}
        Previous Q&A: {json.dumps(previous_answers)}
        Current Difficulty: {self.current_difficulty}
        
        Focus on:
        1. Technical implementation details
        2. Problem-solving approaches
        3. Specific technologies used
        4. Challenges and solutions
        
        Return only the question text, no JSON or additional formatting.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Question generation failed: {str(e)}")
            return cv_analysis["potential_questions"][0]

    def _clean_response(self, text: str) -> str:
        """Clean the response text"""
        text = text.strip()
        if text.startswith("```") and text.endswith("```"):
            text = text[text.find("{"):text.rfind("}")+1]
        elif text.startswith("`") and text.endswith("`"):
            text = text[1:-1]
        return text

    def conduct_interview(self, cv_analysis: Dict):
        """Conduct interactive interview"""
        print("\nStarting Interactive Interview")
        print("=" * 60)
        
        self.interview_results["candidate_name"] = input("\nPlease enter your name: ").strip()
        self.interview_results["position"] = input("Position applying for: ").strip()
        
        # Generate question bank before starting interview
        print("\nGenerating personalized questions...")
        self.generate_question_bank(cv_analysis)
        
        questions_asked = 0
        total_score = 0
        
        try:
            while questions_asked < self.max_questions:
                if questions_asked == 0:
                    # First question about their strongest project
                    question = "Could you describe your most technically challenging project in detail? What were the key problems you solved and technologies you used?"
                else:
                    # Get next question from question bank or generate dynamically
                    next_q = self.get_next_question()
                    if next_q:
                        question = next_q["question"]
                        self.current_difficulty = next_q["difficulty"]
                    else:
                        question = self._get_project_based_question(
                            cv_analysis, 
                            self.interview_results["questions"]
                        )
                
                print(f"\nQuestion {questions_asked + 1} ({self.current_difficulty}):")
                print(f"{question}")
                
                answer = input("\nYour answer (type 'quit' to end): ").strip()
                if answer.lower() in ['quit', 'exit', 'stop']:
                    break
                
                evaluation = self.evaluate_answer(question, answer, cv_analysis)
                
                self.interview_results["questions"].append({
                    "question": question,
                    "answer": answer,
                    "evaluation": evaluation,
                    "difficulty": self.current_difficulty
                })
                
                score = float(evaluation["score"])
                total_score += score
                
                print("\nFeedback:")
                print("-" * 30)
                print(f"Technical Accuracy: {evaluation['technical_accuracy']}/10")
                print(f"Communication: {evaluation['communication']}/10")
                print(f"Feedback: {evaluation['feedback']}")
                print("-" * 30)
                
                questions_asked += 1
                time.sleep(1)
        except Exception as e:
            logger.error(f"Error during interview: {str(e)}")
        finally:
            # Ensure results are saved even if interview is interrupted
            if questions_asked > 0:
                self.interview_results["overall_score"] = total_score / questions_asked
                self._generate_final_feedback()
                self._save_results()

    def _generate_final_feedback(self):
        """Generate final feedback using Gemini"""
        prompt = f"""
        Generate comprehensive feedback for this interview:
        Candidate: {self.interview_results['candidate_name']}
        Position: {self.interview_results['position']}
        Overall Score: {self.interview_results['overall_score']}/10
        
        Interview Details: {json.dumps(self.interview_results['questions'])}
        
        Provide constructive feedback including:
        1. Technical strengths
        2. Areas for improvement
        3. Specific recommendations
        """
        
        try:
            response = self.model.generate_content(prompt)
            self.interview_results["feedback"] = response.text
        except Exception as e:
            logger.error(f"Failed to generate feedback: {str(e)}")
            self.interview_results["feedback"] = "Failed to generate feedback"

    def _save_results(self):
        """Save interview results to JSON file"""
        # Create results directory if it doesn't exist
        results_dir = r"C:\Users\yaduk\OneDrive\Desktop\Projects\major\askAI\Result"
        os.makedirs(results_dir, exist_ok=True)
        
        # Generate filename with timestamp
        filename = os.path.join(
            results_dir, 
            f"interview_{self.interview_results['candidate_name'].lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.interview_results, f, indent=2)
            print(f"\nInterview results saved to {filename}")
            
            # Also save a summary file
            summary_file = os.path.join(results_dir, "interview_summary.json")
            summary = {
                "candidate": self.interview_results['candidate_name'],
                "position": self.interview_results['position'],
                "date": self.interview_results['date'],
                "overall_score": self.interview_results['overall_score'],
                "difficulty_reached": self.current_difficulty,
                "questions_answered": len(self.interview_results['questions']),
                "file_path": filename
            }
            
            # Append or create summary file
            try:
                with open(summary_file, 'r') as f:
                    summaries = json.load(f)
            except:
                summaries = []
            
            summaries.append(summary)
            
            with open(summary_file, 'w') as f:
                json.dump(summaries, f, indent=2)
            
        except Exception as e:
            logger.error(f"Failed to save results: {str(e)}")

    def _default_evaluation(self) -> Dict:
        """Provide default evaluation in case of errors"""
        return {
            "score": 5,
            "feedback": "Evaluation failed",
            "technical_accuracy": 5,
            "communication": 5,
            "suggested_followup": "Could you elaborate on your previous answer?",
            "adjust_difficulty": "maintain",
            "topic_to_explore": "current_topic"
        }

@app.route('/api/analyze-cv', methods=['POST'])
def analyze_cv_endpoint():
    try:
        # Get the PDF file from request
        file = request.files['pdf']
        job_profile = request.form['jobProfile']
        
        # Initialize analyzers
        cv_analyzer = CVAnalyzer()
        cv_analyzer.job_profile = job_profile
        
        # Save PDF temporarily
        temp_path = "temp_cv.pdf"
        file.save(temp_path)
        
        # Analyze CV
        cv_text = cv_analyzer.extract_text_from_pdf(temp_path)
        if not cv_text:
            return jsonify({"error": "Failed to read PDF"}), 400
            
        analysis = cv_analyzer.analyze_cv(cv_text)
        if not analysis:
            return jsonify({"error": "Analysis failed"}), 400
            
        # Remove temp file
        os.remove(temp_path)
        
        return jsonify({
            "analysis": analysis,
            "message": "CV analyzed successfully"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/conduct-interview', methods=['POST'])
def conduct_interview_endpoint():
    try:
        data = request.json
        analysis = data.get('analysis')
        candidate_name = data.get('candidateName')
        position = data.get('position')
        answer = data.get('answer')
        questions_asked = data.get('questionsAsked', 0)  # Track number of questions

        interviewer = InteractiveInterviewer()
        interviewer.interview_results["candidate_name"] = candidate_name
        interviewer.interview_results["position"] = position
        interviewer.questionsAsked = questions_asked  # Set current question count

        # Check if we've reached the maximum questions
        if questions_asked >= interviewer.max_questions:
            return jsonify({
                "evaluation": {
                    "score": 0,
                    "feedback": "Interview complete. Maximum questions reached.",
                    "technical_accuracy": 0,
                    "communication": 0,
                    "interview_complete": True
                },
                "nextQuestion": None
            })

        # Handle interview question/answer
        evaluation = interviewer.evaluate_answer(
            data.get('question', ''),
            answer,
            analysis
        )

        # If interview is complete, don't generate next question
        if interviewer.is_interview_complete:
            return jsonify({
                "evaluation": evaluation,
                "nextQuestion": None,
                "interview_complete": True
            })

        return jsonify({
            "evaluation": evaluation,
            "nextQuestion": interviewer._get_project_based_question(analysis, [])
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    try:
        data = request.json
        email = data.get('email')
        
        # Check if email matches the admin email
        if email != 'pedo@shiazan.com':
            return jsonify({"error": "Invalid admin credentials"}), 401
            
        # Create admin token
        access_token = create_access_token(identity={"email": email, "role": "admin"})
        return jsonify({"token": access_token}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/user/login', methods=['POST'])
def user_login():
    try:
        data = request.json
        email = data.get('email')
        
        if not email:
            return jsonify({"error": "Email required"}), 400
            
        access_token = create_access_token(identity={"email": email, "role": "user"})
        return jsonify({"token": access_token}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/feedback', methods=['GET'])
@jwt_required()
def get_feedback():
    try:
        current_user = get_jwt_identity()
        if current_user.get('role') != 'admin':
            return jsonify({"error": "Unauthorized"}), 403
            
        # Get all interview results
        results_dir = r"C:\Users\yaduk\OneDrive\Desktop\Projects\major\askAI\Result"
        feedback_data = []
        
        for file in os.listdir(results_dir):
            if file.endswith('.json') and file != 'interview_summary.json':
                with open(os.path.join(results_dir, file), 'r') as f:
                    feedback_data.append(json.load(f))
                    
        return jsonify(feedback_data), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)

  
