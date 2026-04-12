import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function LeaveRequestPage({ user }) {
  const [formData, setFormData] = useState({
    leave_type: 'CASUAL',
    start_date: '',
    end_date: '',
    reason: '',
  });
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState(''); // 'success' or 'error'
  const [loading, setLoading] = useState(false);
  const [leaveBalance, setLeaveBalance] = useState(null);
  const isHR = user.role === 'HR';

  useEffect(() => {
    const fetchLeaveBalance = async () => {
      try {
        const response = await axios.get(`${API_URL}/user/profile`, {
          headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        });
        setLeaveBalance(response.data.leave_balance);
      } catch (error) {
      }
    };
    fetchLeaveBalance();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData({ 
      ...formData, 
      [name]: value 
    });
  };

  const calculateDaysRequested = () => {
    if (formData.start_date && formData.end_date) {
      const start = new Date(formData.start_date);
      const end = new Date(formData.end_date);
      return Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1;
    }
    return 0;
  };

  const getAvailableBalance = () => {
    if (!leaveBalance) return null;
    const leaveType = formData.leave_type.toLowerCase();
    return leaveBalance[leaveType]?.remaining || 0;
  };

  const daysRequested = calculateDaysRequested();
  const availableBalance = getAvailableBalance();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage('');
    setLoading(true);

    try {
      const submitData = {
        leave_type: formData.leave_type,
        start_date: formData.start_date,
        end_date: formData.end_date,
        reason: formData.reason,
      };

      await axios.post(`${API_URL}/user/request-leave`, submitData, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });

      setMessage('Leave request submitted successfully!');
      setMessageType('success');
      setFormData({
        leave_type: 'CASUAL',
        start_date: '',
        end_date: '',
        reason: '',
      });

      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Failed to submit leave request';
      setMessage(errorMsg);
      setMessageType('error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h2 className="section-title">Apply for Leave</h2>

      {message && (
        <div className={`alert ${messageType === 'success' ? 'success' : 'error'}`}>
          {message}
        </div>
      )}

      {leaveBalance && (
        <div style={{ 
          backgroundColor: '#f5f5f5', 
          padding: '15px', 
          borderRadius: '4px', 
          marginBottom: '20px',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: '15px',
          textAlign: 'center'
        }}>
          <div>
            <strong>Casual Leave</strong><br />
            Remaining: {leaveBalance.casual.remaining}/{leaveBalance.casual.total}
          </div>
          <div>
            <strong>Sick Leave</strong><br />
            Remaining: {leaveBalance.sick.remaining}/{leaveBalance.sick.total}
          </div>
          <div>
            <strong>Earned Leave</strong><br />
            Remaining: {leaveBalance.earned.remaining}/{leaveBalance.earned.total}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Leave Type</label>
          <select
            name="leave_type"
            value={formData.leave_type}
            onChange={handleChange}
            disabled={loading}
          >
            <option value="CASUAL">Casual Leave</option>
            <option value="SICK">Sick Leave</option>
            <option value="EARNED">Earned Leave</option>
          </select>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
          <div className="form-group">
            <label>Start Date</label>
            <input
              type="date"
              name="start_date"
              value={formData.start_date}
              onChange={handleChange}
              disabled={loading}
              required
            />
          </div>

          <div className="form-group">
            <label>End Date</label>
            <input
              type="date"
              name="end_date"
              value={formData.end_date}
              onChange={handleChange}
              disabled={loading}
              required
            />
          </div>
        </div>

        {daysRequested > 0 && availableBalance !== null && (
          <div style={{
            padding: '10px',
            backgroundColor: availableBalance >= daysRequested ? '#e8f5e9' : '#ffebee',
            border: `1px solid ${availableBalance >= daysRequested ? '#4caf50' : '#f44336'}`,
            borderRadius: '4px',
            marginBottom: '15px',
            color: availableBalance >= daysRequested ? '#2e7d32' : '#c62828'
          }}>
            <strong>Days Requested:</strong> {daysRequested} days | <strong>Available:</strong> {availableBalance} days
            {availableBalance < daysRequested && (
              <div style={{ marginTop: '5px', fontSize: '12px' }}>
                ⚠️ Insufficient balance! You need {daysRequested - availableBalance} more days.
              </div>
            )}
          </div>
        )}

        <div className="form-group">
          <label>Reason</label>
          <textarea
            name="reason"
            value={formData.reason}
            onChange={handleChange}
            placeholder="Please provide reason for leave"
            disabled={loading}
            required
          />
        </div>

        <button 
          type="submit" 
          disabled={loading || (availableBalance !== null && availableBalance < daysRequested && daysRequested > 0)}
        >
          {loading ? 'Submitting...' : 'Submit Leave Request'}
        </button>
      </form>
    </div>
  );
}
