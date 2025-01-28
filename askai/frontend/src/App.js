import React, { useState } from 'react';
import { Container, Paper, Typography } from '@mui/material';
import CVUpload from './components/CVUpload';
import Interview from './components/Interview';
import Login from './components/Login';
import AdminDashboard from './components/AdminDashboard';
import './App.css';

function App() {
  const [step, setStep] = useState('login');
  const [isAdmin, setIsAdmin] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [candidateInfo, setCandidateInfo] = useState({
    name: '',
    position: ''
  });

  const handleLoginSuccess = (adminStatus) => {
    setIsAdmin(adminStatus);
    setStep(adminStatus ? 'admin' : 'upload');
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setStep('login');
    setIsAdmin(false);
  };

  const handleAnalysisComplete = (result) => {
    setAnalysis(result);
    setStep('interview');
  };

  return (
    <Container maxWidth="md">
      <Paper elevation={3} className="main-container">
        <Typography variant="h4" gutterBottom className="title">
          ASKAI
        </Typography>
        <Typography variant="subtitle1" gutterBottom className="subtitle">
          AI-Powered Interview Assistant
        </Typography>

        {step === 'login' && (
          <Login onLoginSuccess={handleLoginSuccess} />
        )}

        {step === 'admin' && (
          <AdminDashboard onLogout={handleLogout} />
        )}

        {step === 'upload' && (
          <CVUpload onAnalysisComplete={handleAnalysisComplete} />
        )}

        {step === 'interview' && (
          <Interview 
            analysis={analysis}
            candidateInfo={candidateInfo}
            setCandidateInfo={setCandidateInfo}
          />
        )}
      </Paper>
    </Container>
  );
}

export default App;
