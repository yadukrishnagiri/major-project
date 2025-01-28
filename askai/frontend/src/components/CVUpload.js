import React, { useState } from 'react';
import { 
  Button, 
  TextField, 
  Box, 
  CircularProgress,
  Typography 
} from '@mui/material';
import { Upload } from '@mui/icons-material';

const CVUpload = ({ onAnalysisComplete }) => {
  const [file, setFile] = useState(null);
  const [jobProfile, setJobProfile] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleFileChange = (event) => {
    setFile(event.target.files[0]);
    setError('');
  };

  const handleUpload = async () => {
    if (!file || !jobProfile) {
      setError('Please select a file and enter job profile');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('pdf', file);
    formData.append('jobProfile', jobProfile);

    try {
      const response = await fetch('http://localhost:5000/api/analyze-cv', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      if (response.ok) {
        onAnalysisComplete(data.analysis);
      } else {
        setError(data.error || 'Failed to analyze CV');
      }
    } catch (err) {
      setError('Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ textAlign: 'center', p: 3 }}>
      <input
        accept="application/pdf"
        style={{ display: 'none' }}
        id="cv-upload"
        type="file"
        onChange={handleFileChange}
      />
      <label htmlFor="cv-upload">
        <Button
          variant="contained"
          component="span"
          startIcon={<Upload />}
          sx={{ mb: 2 }}
        >
          Select CV (PDF)
        </Button>
      </label>
      
      {file && (
        <Typography variant="body2" sx={{ mb: 2 }}>
          Selected: {file.name}
        </Typography>
      )}

      <TextField
        fullWidth
        label="Job Profile"
        value={jobProfile}
        onChange={(e) => setJobProfile(e.target.value)}
        sx={{ mb: 2 }}
      />

      {error && (
        <Typography color="error" sx={{ mb: 2 }}>
          {error}
        </Typography>
      )}

      <Button
        variant="contained"
        color="primary"
        onClick={handleUpload}
        disabled={loading}
      >
        {loading ? <CircularProgress size={24} /> : 'Analyze CV'}
      </Button>
    </Box>
  );
};

export default CVUpload; 