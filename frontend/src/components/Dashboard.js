import React from 'react';
import { Container, Row, Col, Card } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const Dashboard = () => {
  const { user } = useAuth();

  return (
    <Container className="py-5">
      <Row className="mb-4">
        <Col>
          <h1>Dashboard</h1>
          <p className="text-muted">Welcome to LangChef, {user?.full_name || 'User'}!</p>
        </Col>
      </Row>

      <Row>
        <Col md={4} className="mb-3">
          <Card>
            <Card.Body>
              <Card.Title>Playground</Card.Title>
              <Card.Text>
                Try out different models and prompts in the playground.
              </Card.Text>
              <Link to="/playground" className="btn btn-primary">Go to Playground</Link>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={4} className="mb-3">
          <Card>
            <Card.Body>
              <Card.Title>Models</Card.Title>
              <Card.Text>
                View and manage your available models.
              </Card.Text>
              <Link to="/models" className="btn btn-primary">Manage Models</Link>
            </Card.Body>
          </Card>
        </Col>
        
        <Col md={4} className="mb-3">
          <Card>
            <Card.Body>
              <Card.Title>Prompts</Card.Title>
              <Card.Text>
                Create and organize your prompts.
              </Card.Text>
              <Link to="/prompts" className="btn btn-primary">Manage Prompts</Link>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};

export default Dashboard; 