// backend/server.js
const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const dotenv = require('dotenv');
const fileUpload = require('express-fileupload');
const path = require('path'); // ADD THIS

// Load environment variables
dotenv.config();

// Import database connection
const connectDB = require('./config/db');
const drugRoutes = require('./routes/drugs');

// Import routes
const authRoutes = require('./routes/auth');
const reportRoutes = require('./routes/reportAnalysis');
const chatbotRoutes = require('./routes/chatbot');
const symptomRoutes = require('./routes/symptoms');

// Initialize express
const app = express();

// Connect to database
connectDB();

// CORS configuration - UPDATE THIS for production
const corsOptions = {
    origin: process.env.NODE_ENV === 'production' 
        ? true  // Allow all origins in production (since frontend/backend same domain)
        : ['http://localhost:8000', 'http://127.0.0.1:8000'],
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'Origin', 'X-Requested-With', 'Accept']
};
app.use(cors(corsOptions));

// Handle preflight requests
app.options('*', cors(corsOptions));

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(fileUpload({
    limits: { fileSize: 20 * 1024 * 1024 },
    abortOnLimit: true
}));

// IMPORTANT: Serve static files from the project root
// This serves all HTML, CSS, JS, assets from the main directory
app.use(express.static(path.join(__dirname, '../')));

// API Routes
app.use('/api/drugs', drugRoutes);
app.use('/api/auth', authRoutes);
app.use('/api/reports', reportRoutes);
app.use('/api/chatbot', chatbotRoutes);
app.use('/api/symptoms', symptomRoutes);

// Health check route (keep this for testing)
app.get('/api/health', (req, res) => {
    res.json({ 
        status: 'healthy', 
        services: {
            backend: 'running',
            timestamp: new Date().toISOString()
        }
    });
});

// IMPORTANT: For any non-API request, serve index.html
// This enables client-side routing
app.get('*', (req, res, next) => {
    // Skip API routes
    if (req.path.startsWith('/api/')) {
        return next();
    }
    
    // Serve index.html for all other routes
    res.sendFile(path.join(__dirname, '../index.html'));
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ message: 'Something went wrong!' });
});

// Start server
const PORT = process.env.PORT || 5000;
app.listen(PORT, '0.0.0.0', () => {
    console.log(`✅ Server running on port ${PORT}`);
    console.log(`📁 Serving static files from: ${path.join(__dirname, '../')}`);
    console.log(`🌐 Environment: ${process.env.NODE_ENV || 'development'}`);
});