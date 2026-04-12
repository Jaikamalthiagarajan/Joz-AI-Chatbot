import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function DashboardPage({ user }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/user/profile`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      setProfile(response.data);
      setError('');
    } catch (err) {
      setError('Failed to load profile');
      setProfile({
        username: user.username,
        department: 'N/A',
        leave_balance: {
          casual: { total: 0, taken: 0, remaining: 0 },
          sick: { total: 0, taken: 0, remaining: 0 },
          earned: { total: 0, taken: 0, remaining: 0 }
        }
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="container"><div style={{ textAlign: 'center', padding: '40px' }}>Loading...</div></div>;
  }

  return (
    <div className="container">
      <h2 className="section-title">Dashboard</h2>

      {error && <div className="alert error">{error}</div>}

      {profile && (
        <>
          {/* Show leave balance cards only for EMPLOYEE role */}
          {(profile.role || user.role) === 'EMPLOYEE' && (
            <div className="stats-grid">
              <div className="stat-card">
                <div className="label">Casual Leave</div>
                <div className="value">{profile.leave_balance.casual.remaining}</div>
                <div className="label">Remaining</div>
              </div>

              <div className="stat-card">
                <div className="label">Sick Leave</div>
                <div className="value">{profile.leave_balance.sick.remaining}</div>
                <div className="label">Remaining</div>
              </div>

              <div className="stat-card">
                <div className="label">Earned Leave</div>
                <div className="value">{profile.leave_balance.earned.remaining}</div>
                <div className="label">Remaining</div>
              </div>
            </div>
          )}

          {/* HR welcome message */}
          {(profile.role || user.role) === 'HR' && (
            <div style={{
              backgroundColor: '#e3f2fd',
              border: '1px solid #1976d2',
              borderRadius: '4px',
              padding: '20px',
              marginBottom: '20px',
              textAlign: 'center'
            }}>
              <strong style={{ fontSize: '16px' }}>Welcome to HR Dashboard!</strong><br />
              <span style={{ color: '#555' }}>Go to <strong>HR Management</strong> to manage employees and leave requests.</span>
            </div>
          )}

          <div className="profile-info" style={{ backgroundColor: '#f5f5f5', padding: '30px', borderRadius: '8px', marginBottom: '30px' }}>
            <h3 style={{ marginBottom: '20px', fontSize: '18px', color: '#333' }}>Employee Information</h3>
            <div style={{ display: 'flex', gap: '80px', marginBottom: '40px', alignItems: 'center', flexWrap: 'wrap', paddingBottom: '20px', borderBottom: '2px solid #ddd' }}>
              <div style={{ padding: '10px 0' }}>
                <p style={{ margin: '0', fontSize: '15px' }}><strong>Username:</strong> <span style={{ marginLeft: '10px', color: '#555' }}>{profile.username}</span></p>
              </div>
              <div style={{ padding: '10px 0' }}>
                <p style={{ margin: '0', fontSize: '15px' }}><strong>Role:</strong> <span style={{ 
                  backgroundColor: (profile.role || user.role) === 'HR' ? '#ffb74d' : '#81c784',
                  color: 'white',
                  padding: '6px 12px',
                  borderRadius: '4px',
                  fontWeight: 'bold',
                  marginLeft: '10px'
                }}>
                  {profile.role || user.role || 'N/A'}
                </span></p>
              </div>
              <div style={{ padding: '10px 0' }}>
                <p style={{ margin: '0', fontSize: '15px' }}><strong>Department:</strong> <span style={{ marginLeft: '10px', color: '#555' }}>{profile.department || 'N/A'}</span></p>
              </div>
            </div>

            {/* Show leave balance table for both roles */}
            <h3 style={{ marginTop: '30px', marginBottom: '20px', fontSize: '18px', color: '#333' }}>Leave Information</h3>
            <table className="table" style={{ width: '100%', marginTop: '15px', marginBottom: '20px' }}>
              <thead>
                <tr>
                  <th style={{ padding: '15px', textAlign: 'left', backgroundColor: '#e0e0e0', fontWeight: 'bold' }}>Leave Type</th>
                  <th style={{ padding: '15px', textAlign: 'center', backgroundColor: '#e0e0e0', fontWeight: 'bold' }}>Total</th>
                  <th style={{ padding: '15px', textAlign: 'center', backgroundColor: '#e0e0e0', fontWeight: 'bold' }}>Taken</th>
                  <th style={{ padding: '15px', textAlign: 'center', backgroundColor: '#e0e0e0', fontWeight: 'bold' }}>Remaining</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid #ddd' }}>
                  <td style={{ padding: '15px', textAlign: 'left' }}>Casual</td>
                  <td style={{ padding: '15px', textAlign: 'center' }}>{profile.leave_balance.casual.total}</td>
                  <td style={{ padding: '15px', textAlign: 'center' }}>{profile.leave_balance.casual.taken}</td>
                  <td style={{ padding: '15px', textAlign: 'center', fontWeight: 'bold', color: '#2e7d32' }}>{profile.leave_balance.casual.remaining}</td>
                </tr>
                <tr style={{ borderBottom: '1px solid #ddd' }}>
                  <td style={{ padding: '15px', textAlign: 'left' }}>Sick</td>
                  <td style={{ padding: '15px', textAlign: 'center' }}>{profile.leave_balance.sick.total}</td>
                  <td style={{ padding: '15px', textAlign: 'center' }}>{profile.leave_balance.sick.taken}</td>
                  <td style={{ padding: '15px', textAlign: 'center', fontWeight: 'bold', color: '#2e7d32' }}>{profile.leave_balance.sick.remaining}</td>
                </tr>
                <tr>
                  <td style={{ padding: '15px', textAlign: 'left' }}>Earned</td>
                  <td style={{ padding: '15px', textAlign: 'center' }}>{profile.leave_balance.earned.total}</td>
                  <td style={{ padding: '15px', textAlign: 'center' }}>{profile.leave_balance.earned.taken}</td>
                  <td style={{ padding: '15px', textAlign: 'center', fontWeight: 'bold', color: '#2e7d32' }}>{profile.leave_balance.earned.remaining}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: '30px', textAlign: 'center' }}>
            <button onClick={fetchProfile} style={{ padding: '12px 30px', cursor: 'pointer', backgroundColor: '#2e7d32', color: 'white', border: 'none', borderRadius: '4px', fontSize: '14px', fontWeight: 'bold' }}>
              Refresh
            </button>
          </div>
        </>
      )}
    </div>
  );
}
