import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Button,
  Typography,
  Paper,
  Rating,
  CircularProgress
} from '@mui/material';

const Interview = ({ analysis, candidateInfo, setCandidateInfo }) => {
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [questionsAsked, setQuestionsAsked] = useState(0);

  useEffect(() => {
    // Set initial question
    setCurrentQuestion(
      "Could you describe your most technically challenging project in detail? What were the key problems you solved and technologies you used?"
    );
  }, []);

  const handleSubmitAnswer = async () => {
    if (!answer.trim()) return;
    
    setLoading(true);
    try {
      const response = await fetch('http://localhost:5000/api/conduct-interview', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          analysis,
          candidateName: candidateInfo.name,
          position: candidateInfo.position,
          question: currentQuestion,
          answer,
          questionsAsked: questionsAsked,
        }),
      });

      const data = await response.json();
      if (response.ok) {
        setEvaluation(data.evaluation);
        
        if (data.interview_complete || !data.nextQuestion) {
          setCurrentQuestion('Interview Complete');
          return;
        }
        
        setCurrentQuestion(data.nextQuestion);
        setAnswer('');
        setQuestionsAsked(prev => prev + 1);
      }
    } catch (error) {
      console.error('Interview error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      {currentQuestion === 'Interview Complete' ? (
        <Typography variant="h6" color="primary" sx={{ mt: 3 }}>
          Interview Complete! Thank you for your participation.
        </Typography>
      ) : (
        <>
          <Typography variant="h6" gutterBottom>
            Question {questionsAsked + 1}/10:
          </Typography>
          <Typography variant="body1" sx={{ mb: 3 }}>
            {currentQuestion}
          </Typography>

          <TextField
            fullWidth
            multiline
            rows={4}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Type your answer here..."
            sx={{ mb: 2 }}
          />

          <Button
            variant="contained"
            onClick={handleSubmitAnswer}
            disabled={loading || !answer.trim()}
          >
            {loading ? <CircularProgress size={24} /> : 'Submit Answer'}
          </Button>

          {evaluation && (
            <Paper sx={{ mt: 3, p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Feedback:
              </Typography>
              <Box sx={{ mb: 2 }}>
                <Typography component="legend">Technical Accuracy</Typography>
                <Rating value={evaluation.technical_accuracy / 2} readOnly />
              </Box>
              <Box sx={{ mb: 2 }}>
                <Typography component="legend">Communication</Typography>
                <Rating value={evaluation.communication / 2} readOnly />
              </Box>
              <Typography variant="body1">
                {evaluation.feedback}
              </Typography>
            </Paper>
          )}
        </>
      )}
    </Box>
  );
};

export default Interview; 