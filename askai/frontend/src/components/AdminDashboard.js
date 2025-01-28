import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button
} from '@mui/material';

const AdminDashboard = ({ onLogout }) => {
  const [feedback, setFeedback] = useState([]);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchFeedback();
  }, []);

  const fetchFeedback = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/admin/feedback', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      const data = await response.json();
      if (response.ok) {
        setFeedback(data);
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError('Failed to fetch feedback');
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h5">Admin Dashboard</Typography>
        <Button variant="outlined" onClick={onLogout}>
          Logout
        </Button>
      </Box>

      {error ? (
        <Typography color="error">{error}</Typography>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Candidate</TableCell>
                <TableCell>Position</TableCell>
                <TableCell>Date</TableCell>
                <TableCell>Overall Score</TableCell>
                <TableCell>Details</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {feedback.map((item, index) => (
                <TableRow key={index}>
                  <TableCell>{item.candidate_name}</TableCell>
                  <TableCell>{item.position}</TableCell>
                  <TableCell>{item.date}</TableCell>
                  <TableCell>{item.overall_score.toFixed(2)}/10</TableCell>
                  <TableCell>
                    <Button size="small" onClick={() => console.log(item)}>
                      View Details
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default AdminDashboard; 