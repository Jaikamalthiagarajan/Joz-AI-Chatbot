import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function HRManagementPage({ user }) {
  const [pendingLeaves, setPendingLeaves] = useState([]);
  const [showAddEmployee, setShowAddEmployee] = useState(false);
  const [formMessage, setFormMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [file, setFile] = useState(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [downloadMessage, setDownloadMessage] = useState('');
  const [employeeForm, setEmployeeForm] = useState({
    username: '',
    password: '',
    role: 'EMPLOYEE',
    department: '',
    casual_total: 12,
    sick_total: 7,
    earned_total: 18
  });

  useEffect(() => {
    if (user.role === 'HR') {
      fetchPendingLeaves();
    }
  }, []);

  const fetchPendingLeaves = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API_URL}/hr/pending-leaves`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      if (Array.isArray(response.data)) {
        setPendingLeaves(response.data);
      }
    } catch (err) {
      // Handle error silently
    } finally {
      setLoading(false);
    }
  };

  const approveLeave = async (requestId) => {
    try {
      await axios.put(`${API_URL}/hr/approve-leave/${requestId}`, {}, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      setFormMessage('Leave approved successfully!');
      fetchPendingLeaves();
      setTimeout(() => setFormMessage(''), 3000);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to approve leave';
      setFormMessage(errorMsg);
      setTimeout(() => setFormMessage(''), 5000);
    }
  };

  const rejectLeave = async (requestId) => {
    try {
      await axios.put(`${API_URL}/hr/reject-leave/${requestId}`, {}, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      setFormMessage('Leave rejected successfully!');
      fetchPendingLeaves();
      setTimeout(() => setFormMessage(''), 3000);
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to reject leave';
      setFormMessage(errorMsg);
      setTimeout(() => setFormMessage(''), 5000);
    }
  };

  const handleEmployeeFormChange = (e) => {
    const { name, value } = e.target;
    setEmployeeForm({
      ...employeeForm,
      [name]: name.includes('_total') ? parseInt(value) : value
    });
  };

  const handleAddEmployee = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/hr/add-employee`, employeeForm, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      setFormMessage('Employee added successfully!');
      setEmployeeForm({
        username: '',
        password: '',
        role: 'EMPLOYEE',
        department: '',
        casual_total: 12,
        sick_total: 7,
        earned_total: 18
      });
      setShowAddEmployee(false);
      setTimeout(() => setFormMessage(''), 3000);
    } catch (err) {
      setFormMessage(err.response?.data?.detail || 'Failed to add employee');
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    
    if (selectedFile) {
      if (!selectedFile.name.endsWith('.pdf')) {
        setFormMessage('Only PDF files are allowed');
        setTimeout(() => setFormMessage(''), 3000);
        setFile(null);
        return;
      }
      
      if (selectedFile.size > 50 * 1024 * 1024) {
        setFormMessage('File size must be less than 50 MB');
        setTimeout(() => setFormMessage(''), 3000);
        setFile(null);
        return;
      }
      
      setFile(selectedFile);
    }
  };

  const handlePolicyUpload = async (e) => {
    e.preventDefault();
    
    if (!file) {
      setFormMessage('Please select a PDF file');
      return;
    }

    setUploadLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      await axios.post(`${API_URL}/hr/upload-policy`, formData, {
        headers: { 
          Authorization: `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'multipart/form-data'
        },
      });

      setFormMessage(`Policy "${file.name}" uploaded successfully!`);
      setFile(null);
      
      const fileInput = document.getElementById('policy-file-input');
      if (fileInput) fileInput.value = '';

      setTimeout(() => setFormMessage(''), 3000);
    } catch (error) {
      const errorMsg = error.response?.data?.detail || 'Failed to upload policy';
      setFormMessage(errorMsg);
      setTimeout(() => setFormMessage(''), 3000);
    } finally {
      setUploadLoading(false);
    }
  };

  const downloadReport = async (format) => {
    setDownloadLoading(true);
    setDownloadMessage('');
    
    try {
      const currentYear = new Date().getFullYear();
      const response = await axios.get(`${API_URL}/hr/download-report/${format}?year=${currentYear}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      const fileExtension = format === 'csv' ? 'csv' : format === 'excel' ? 'xlsx' : 'pdf';
      link.setAttribute('download', `leave_analytics_${currentYear}.${fileExtension}`);
      
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);

      setDownloadMessage(`Report downloaded as ${format.toUpperCase()} successfully!`);
      setTimeout(() => setDownloadMessage(''), 3000);
    } catch (error) {
      const errorMsg = error.response?.data?.detail || `Failed to download ${format} report`;
      setDownloadMessage(errorMsg);
      setTimeout(() => setDownloadMessage(''), 3000);
    } finally {
      setDownloadLoading(false);
    }
  };

  if (user.role !== 'HR') {
    return (
      <div className="container">
        <div className="alert error">Access Denied - HR Only</div>
      </div>
    );
  }

  return (
    <div className="container">
      <h2 className="section-title">HR Management</h2>

      {formMessage && (
        <div className={`alert ${formMessage.includes('successfully') ? 'success' : 'error'}`}>
          {formMessage}
        </div>
      )}

      {/* Add Employee Section */}
      <div style={{
        backgroundColor: '#f0f4ff',
        border: '1px solid #1976d2',
        borderRadius: '4px',
        padding: '20px',
        marginBottom: '30px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h3 style={{ margin: 0 }}>Employee Management</h3>
          <button
            onClick={() => setShowAddEmployee(!showAddEmployee)}
            style={{
              backgroundColor: '#4caf50',
              color: 'white',
              border: 'none',
              padding: '10px 20px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            {showAddEmployee ? 'Cancel' : '+ Add New Employee'}
          </button>
        </div>

        {showAddEmployee && (
          <form onSubmit={handleAddEmployee} style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
            <div>
              <label><strong>Username *</strong></label>
              <input
                type="text"
                name="username"
                value={employeeForm.username}
                onChange={handleEmployeeFormChange}
                required
                style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ddd', boxSizing: 'border-box' }}
              />
            </div>
            <div>
              <label><strong>Password *</strong></label>
              <input
                type="password"
                name="password"
                value={employeeForm.password}
                onChange={handleEmployeeFormChange}
                required
                style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ddd', boxSizing: 'border-box' }}
              />
            </div>
            <div>
              <label><strong>Role *</strong></label>
              <select
                name="role"
                value={employeeForm.role}
                onChange={handleEmployeeFormChange}
                style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ddd', boxSizing: 'border-box' }}
              >
                <option value="EMPLOYEE">Employee</option>
                <option value="HR">HR</option>
              </select>
            </div>
            <div>
              <label><strong>Department *</strong></label>
              <input
                type="text"
                name="department"
                value={employeeForm.department}
                onChange={handleEmployeeFormChange}
                required
                style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ddd', boxSizing: 'border-box' }}
              />
            </div>
            <div>
              <label><strong>Casual Leave Days</strong></label>
              <input
                type="number"
                name="casual_total"
                value={employeeForm.casual_total}
                onChange={handleEmployeeFormChange}
                style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ddd', boxSizing: 'border-box' }}
              />
            </div>
            <div>
              <label><strong>Sick Leave Days</strong></label>
              <input
                type="number"
                name="sick_total"
                value={employeeForm.sick_total}
                onChange={handleEmployeeFormChange}
                style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ddd', boxSizing: 'border-box' }}
              />
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <label><strong>Earned Leave Days</strong></label>
              <input
                type="number"
                name="earned_total"
                value={employeeForm.earned_total}
                onChange={handleEmployeeFormChange}
                style={{ width: '100%', padding: '10px', borderRadius: '4px', border: '1px solid #ddd', boxSizing: 'border-box' }}
              />
            </div>
            <button
              type="submit"
              style={{
                gridColumn: '1 / -1',
                backgroundColor: '#2196f3',
                color: 'white',
                border: 'none',
                padding: '12px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '16px',
                fontWeight: 'bold'
              }}
            >
              Add Employee
            </button>
          </form>
        )}
      </div>

      {/* Leave Approval Section */}
      <div style={{
        backgroundColor: '#f9f9f9',
        border: '1px solid #ddd',
        borderRadius: '4px',
        padding: '20px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h3 style={{ margin: 0 }}>Pending Leave Requests</h3>
          <button
            onClick={fetchPendingLeaves}
            style={{
              backgroundColor: '#2196f3',
              color: 'white',
              border: 'none',
              padding: '8px 15px',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <p style={{ textAlign: 'center', color: '#666' }}>Loading pending leaves...</p>
        ) : pendingLeaves.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ backgroundColor: '#f0f0f0', borderBottom: '2px solid #ddd' }}>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Employee ID</th>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Leave Type</th>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Start Date</th>
                  <th style={{ padding: '12px', textAlign: 'left' }}>End Date</th>
                  <th style={{ padding: '12px', textAlign: 'left' }}>Reason</th>
                  <th style={{ padding: '12px', textAlign: 'center' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {pendingLeaves.map((leave) => (
                  <tr key={leave.request_id} style={{ borderBottom: '1px solid #ddd' }}>
                    <td style={{ padding: '12px' }}>{leave.employee_id}</td>
                    <td style={{ padding: '12px' }}>
                      <span style={{
                        backgroundColor: leave.leave_type === 'CASUAL' ? '#ffeb3b' : leave.leave_type === 'SICK' ? '#f44336' : '#4caf50',
                        color: '#000',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '12px',
                        fontWeight: 'bold'
                      }}>
                        {leave.leave_type}
                      </span>
                    </td>
                    <td style={{ padding: '12px' }}>{new Date(leave.start_date).toLocaleDateString()}</td>
                    <td style={{ padding: '12px' }}>{new Date(leave.end_date).toLocaleDateString()}</td>
                    <td style={{ padding: '12px' }}>{leave.reason}</td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      <button
                        onClick={() => approveLeave(leave.request_id)}
                        style={{
                          backgroundColor: '#4caf50',
                          color: 'white',
                          border: 'none',
                          padding: '6px 12px',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          marginRight: '8px',
                          fontSize: '12px'
                        }}
                        title="Approve"
                      >
                        ✓ Approve
                      </button>
                      <button
                        onClick={() => rejectLeave(leave.request_id)}
                        style={{
                          backgroundColor: '#f44336',
                          color: 'white',
                          border: 'none',
                          padding: '6px 12px',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontSize: '12px'
                        }}
                        title="Reject"
                      >
                        ✗ Reject
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p style={{ color: '#666', fontStyle: 'italic', textAlign: 'center' }}>No pending leave requests at this time</p>
        )}
      </div>

      {/* Leave Analytics & Reports Section */}
      <div style={{
        backgroundColor: '#e8f5e9',
        border: '1px solid #4caf50',
        borderRadius: '4px',
        padding: '20px',
        marginTop: '30px'
      }}>
        <h3 style={{ margin: '0 0 20px 0', color: '#2e7d32' }}>Leave Analytics & Reports</h3>
        
        {downloadMessage && (
          <div style={{
            padding: '12px',
            backgroundColor: downloadMessage.includes('successfully') ? '#c8e6c9' : '#ffcdd2',
            borderRadius: '4px',
            marginBottom: '15px',
            color: downloadMessage.includes('successfully') ? '#1b5e20' : '#b71c1c'
          }}>
            {downloadMessage}
          </div>
        )}

        <p style={{ color: '#555', marginBottom: '15px' }}>
          Download leave consumption analytics and trends in your preferred format:
        </p>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
          gap: '12px'
        }}>
          <button
            onClick={() => downloadReport('csv')}
            disabled={downloadLoading}
            style={{
              backgroundColor: '#4caf50',
              color: 'white',
              border: 'none',
              padding: '12px 20px',
              borderRadius: '4px',
              cursor: downloadLoading ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 'bold',
              opacity: downloadLoading ? 0.6 : 1
            }}
            title="Download as CSV file"
          >
            CSV
          </button>

          <button
            onClick={() => downloadReport('excel')}
            disabled={downloadLoading}
            style={{
              backgroundColor: '#2196f3',
              color: 'white',
              border: 'none',
              padding: '12px 20px',
              borderRadius: '4px',
              cursor: downloadLoading ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 'bold',
              opacity: downloadLoading ? 0.6 : 1
            }}
            title="Download as Excel file"
          >
            Excel
          </button>

          <button
            onClick={() => downloadReport('pdf')}
            disabled={downloadLoading}
            style={{
              backgroundColor: '#f44336',
              color: 'white',
              border: 'none',
              padding: '12px 20px',
              borderRadius: '4px',
              cursor: downloadLoading ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 'bold',
              opacity: downloadLoading ? 0.6 : 1
            }}
            title="Download as PDF file"
          >
            PDF
          </button>
        </div>

        <p style={{ fontSize: '12px', color: '#888', marginTop: '15px', marginBottom: 0 }}>
          Reports include up-to-date leave consumption data, employee-wise breakdown, and year-over-year trends.
        </p>
      </div>
      <div style={{
        backgroundColor: '#fff3e0',
        border: '1px solid #ff9800',
        borderRadius: '4px',
        padding: '20px',
        marginTop: '30px'
      }}>
        <h3 style={{ margin: '0 0 20px 0', color: '#e65100' }}>Upload HR Policy</h3>
        
        <form onSubmit={handlePolicyUpload}>
          <div style={{
            border: '2px dashed #ff9800',
            borderRadius: '4px',
            padding: '20px',
            textAlign: 'center',
            backgroundColor: '#fffde7',
            marginBottom: '15px'
          }}>
            <input
              id="policy-file-input"
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              disabled={uploadLoading}
              style={{ display: 'none' }}
            />
            <label htmlFor="policy-file-input" style={{ cursor: 'pointer' }}>
              <div style={{ fontSize: '28px', marginBottom: '10px' }}>📋</div>
              <p style={{ margin: '0 0 5px 0', color: '#ff9800', fontWeight: 'bold' }}>
                Click to select or drag a PDF file
              </p>
              <p style={{ margin: '0', color: '#999', fontSize: '12px' }}>
                Only PDF files, maximum 50 MB
              </p>
            </label>
          </div>

          {file && (
            <div style={{
              padding: '12px',
              backgroundColor: '#e3f2fd',
              borderRadius: '4px',
              marginBottom: '15px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <div>
                <strong>Selected:</strong> {file.name}
                <div style={{ fontSize: '12px', color: '#666', marginTop: '5px' }}>
                  Size: {(file.size / 1024).toFixed(2)} KB
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setFile(null);
                  document.getElementById('policy-file-input').value = '';
                }}
                style={{
                  backgroundColor: '#ff6b6b',
                  color: 'white',
                  border: 'none',
                  padding: '6px 12px',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '12px'
                }}
              >
                Remove
              </button>
            </div>
          )}

          <button 
            type="submit" 
            disabled={uploadLoading || !file}
            style={{
              width: '100%',
              padding: '12px',
              backgroundColor: file && !uploadLoading ? '#ff9800' : '#ccc',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              fontSize: '16px',
              fontWeight: 'bold',
              cursor: file && !uploadLoading ? 'pointer' : 'not-allowed'
            }}
          >
            {uploadLoading ? 'Uploading...' : 'Upload Policy'}
          </button>
        </form>
      </div>
    </div>
  );
}
