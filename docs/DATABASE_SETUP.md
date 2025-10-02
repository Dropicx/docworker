# Database Setup Guide

This guide explains how to set up PostgreSQL database for the DocTranslator application.

## Railway PostgreSQL Setup

### 1. Add PostgreSQL Service to Railway

1. Go to your Railway project dashboard
2. Click "New Service" → "Database" → "PostgreSQL"
3. Railway will automatically provision a PostgreSQL database
4. Note the connection details from the service

### 2. Environment Variables

Add these environment variables to your Railway project:

```bash
# Primary database connection (Railway provides this automatically)
DATABASE_URL=postgresql://username:password@hostname:port/database_name

# Alternative: Individual components (if DATABASE_URL is not available)
POSTGRES_HOST=your_postgres_host
POSTGRES_PORT=5432
POSTGRES_DB=doctranslator
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password
```

### 3. Database Initialization

The database tables will be created automatically when the application starts. You can also initialize them manually:

```bash
# Initialize database tables
python app/database/init_db.py

# Drop all tables (use with caution!)
python app/database/init_db.py drop
```

## Database Schema

### Tables Created

1. **document_prompts** - Stores prompt configurations for each document type
2. **pipeline_step_configs** - Stores pipeline step enable/disable settings
3. **ai_interaction_logs** - Comprehensive logging of all AI interactions
4. **system_settings** - System-wide configuration settings
5. **user_sessions** - User authentication sessions

### Key Features

- **Comprehensive Logging**: Every AI interaction is logged with input/output, timing, and metadata
- **Analytics Ready**: Built-in analytics queries for processing insights
- **Scalable**: Designed to handle high-volume processing
- **Audit Trail**: Complete history of all prompt changes and processing

## Analytics and Monitoring

### Available Analytics

- Processing success rates by step
- Average processing times
- Confidence score distributions
- Error analysis and debugging
- User behavior tracking
- Performance metrics

### Logging Details

Each AI interaction logs:
- Input and output text
- Processing time
- Confidence scores
- Model used
- Error messages
- User context
- Timestamps

## Local Development

For local development, the application will fall back to SQLite if PostgreSQL is not configured:

```bash
# No database configuration needed for local development
# SQLite will be used automatically
```

## Migration from File-Based System

The new database system is backward compatible. Existing file-based prompts will be migrated automatically on first run.

## Troubleshooting

### Common Issues

1. **Connection Errors**: Check DATABASE_URL format and credentials
2. **Permission Errors**: Ensure database user has CREATE/ALTER permissions
3. **Timeout Errors**: Check network connectivity to Railway

### Debug Mode

Enable SQL query logging by setting:
```bash
DEBUG=true
LOG_LEVEL=DEBUG
```

This will show all SQL queries in the logs for debugging.
