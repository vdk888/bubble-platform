"""
Tests for Celery worker health monitoring endpoints.

Tests the new health endpoints added for Step 5:
- /health/workers - Worker status monitoring
- /health/workers/progress/{task_id} - Task progress tracking
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app


class TestWorkerHealthEndpoints:
    """Test worker health monitoring endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_worker_health_check_healthy(self, client):
        """Test worker health check when workers are healthy"""
        
        with patch('app.api.v1.health.get_worker_status') as mock_get_status:
            # Mock healthy worker status
            mock_get_status.return_value = {
                'status': 'healthy',
                'workers': 2,
                'active_tasks': 3,
                'worker_stats': {
                    'worker1': {'total': {'tasks': 100}},
                    'worker2': {'total': {'tasks': 85}}
                }
            }
            
            response = client.get("/health/workers")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['success'] is True
            assert data['data']['worker_status'] == 'healthy'
            assert data['data']['active_workers'] == 2
            assert data['data']['active_tasks'] == 3
            assert 'Found 2 active workers' in data['message']
            assert 'view_task_progress' in data['next_actions']
    
    def test_worker_health_check_no_workers(self, client):
        """Test worker health check when no workers are available"""
        
        with patch('app.api.v1.health.get_worker_status') as mock_get_status:
            # Mock no workers available
            mock_get_status.return_value = {
                'status': 'unhealthy',
                'workers': 0,
                'active_tasks': 0,
                'message': 'No workers available'
            }
            
            response = client.get("/health/workers")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['success'] is False
            assert data['data']['worker_status'] == 'unhealthy'
            assert data['data']['active_workers'] == 0
            assert data['data']['active_tasks'] == 0
            assert 'Found 0 active workers' in data['message']
            assert 'start_workers' in data['next_actions']
    
    def test_worker_health_check_error(self, client):
        """Test worker health check when there's an error"""
        
        with patch('app.api.v1.health.get_worker_status') as mock_get_status:
            # Mock error condition
            mock_get_status.side_effect = Exception("Connection failed")
            
            response = client.get("/health/workers")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['success'] is False
            assert data['data']['worker_status'] == 'error'
            assert data['data']['active_workers'] == 0
            assert 'Connection failed' in data['data']['error']
            assert 'check_celery_broker' in data['next_actions']
    
    def test_get_task_progress_found(self, client):
        """Test getting task progress for existing task"""
        
        task_id = "test-task-123"
        
        with patch('app.api.v1.health.get_task_progress') as mock_get_progress:
            # Mock progress information
            mock_progress = {
                'status': 'in_progress',
                'progress': '75',
                'symbol': 'AAPL',
                'started_at': datetime.now(timezone.utc).isoformat(),
                'user_id': 'test-user'
            }
            mock_get_progress.return_value = mock_progress
            
            response = client.get(f"/health/workers/progress/{task_id}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['success'] is True
            assert data['data']['task_id'] == task_id
            assert data['data']['progress_info'] == mock_progress
            assert f'Task progress retrieved for {task_id}' in data['message']
            assert 'wait_for_completion' in data['next_actions']
    
    def test_get_task_progress_completed(self, client):
        """Test getting progress for completed task"""
        
        task_id = "completed-task-456"
        
        with patch('app.api.v1.health.get_task_progress') as mock_get_progress:
            # Mock completed task progress
            mock_progress = {
                'status': 'completed',
                'progress': '100',
                'symbol': 'MSFT',
                'started_at': datetime.now(timezone.utc).isoformat(),
                'completed_at': datetime.now(timezone.utc).isoformat(),
                'result': '{"success": true, "validated": true}',
                'user_id': 'test-user'
            }
            mock_get_progress.return_value = mock_progress
            
            response = client.get(f"/health/workers/progress/{task_id}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['success'] is True
            assert data['data']['progress_info']['status'] == 'completed'
            assert 'check_results' in data['next_actions']
    
    def test_get_task_progress_not_found(self, client):
        """Test getting progress for non-existent task"""
        
        task_id = "nonexistent-task"
        
        with patch('app.api.v1.health.get_task_progress') as mock_get_progress:
            # Mock task not found
            mock_get_progress.return_value = None
            
            response = client.get(f"/health/workers/progress/{task_id}")
            
            assert response.status_code == 404
            data = response.json()
            
            assert data['detail']['success'] is False
            assert f'Task {task_id} not found' in data['detail']['message']
            assert 'check_task_id' in data['detail']['next_actions']
    
    def test_get_task_progress_error(self, client):
        """Test getting progress when there's an error"""
        
        task_id = "error-task"
        
        with patch('app.api.v1.health.get_task_progress') as mock_get_progress:
            # Mock error condition
            mock_get_progress.side_effect = Exception("Redis connection failed")
            
            response = client.get(f"/health/workers/progress/{task_id}")
            
            assert response.status_code == 500
            data = response.json()
            
            assert data['detail']['success'] is False
            assert 'Failed to retrieve task progress' in data['detail']['message']
            assert 'check_redis_connection' in data['detail']['next_actions']


class TestWorkerHealthIntegration:
    """Integration tests for worker health monitoring"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_worker_health_ai_friendly_response_format(self, client):
        """Test that worker health responses follow AI-friendly format"""
        
        with patch('app.api.v1.health.get_worker_status') as mock_get_status:
            mock_get_status.return_value = {
                'status': 'healthy',
                'workers': 1,
                'active_tasks': 0
            }
            
            response = client.get("/health/workers")
            data = response.json()
            
            # Verify AI-friendly response structure
            required_fields = ['success', 'data', 'message', 'next_actions']
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
            
            # Verify data structure
            assert 'worker_status' in data['data']
            assert 'active_workers' in data['data']
            assert 'active_tasks' in data['data']
            assert 'timestamp' in data['data']
            
            # Verify next_actions are relevant
            assert isinstance(data['next_actions'], list)
            assert len(data['next_actions']) > 0
    
    def test_task_progress_ai_friendly_response_format(self, client):
        """Test that task progress responses follow AI-friendly format"""
        
        task_id = "test-task"
        
        with patch('app.api.v1.health.get_task_progress') as mock_get_progress:
            mock_get_progress.return_value = {
                'status': 'in_progress',
                'progress': '50'
            }
            
            response = client.get(f"/health/workers/progress/{task_id}")
            data = response.json()
            
            # Verify AI-friendly response structure
            required_fields = ['success', 'data', 'message', 'next_actions']
            for field in required_fields:
                assert field in data, f"Missing required field: {field}"
            
            # Verify data structure
            assert 'task_id' in data['data']
            assert 'progress_info' in data['data']
            assert 'timestamp' in data['data']
            
            # Verify next_actions are context-appropriate
            assert isinstance(data['next_actions'], list)
            assert len(data['next_actions']) > 0
    
    def test_health_endpoints_consistency(self, client):
        """Test consistency across health monitoring endpoints"""
        
        # Test main health endpoint
        response = client.get("/health/")
        main_health = response.json()
        
        # Test worker health endpoint
        with patch('app.api.v1.health.get_worker_status') as mock_status:
            mock_status.return_value = {'status': 'healthy', 'workers': 1, 'active_tasks': 0}
            
            response = client.get("/health/workers")
            worker_health = response.json()
        
        # Verify both follow same response format
        common_fields = ['success', 'data', 'message', 'next_actions']
        for field in common_fields:
            assert field in main_health
            assert field in worker_health
        
        # Verify timestamps are present and properly formatted
        assert 'timestamp' in main_health['data']
        assert 'timestamp' in worker_health['data']


# Test markers
pytestmark = [
    pytest.mark.health_monitoring,
    pytest.mark.api_endpoints
]