# DocTranslator Documentation Index

Complete documentation for the DocTranslator medical document translation platform.

---

## 📘 User Guides

### [Pipeline User Guide](PIPELINE_USER_GUIDE.md) ⭐ **NEW**
**Complete guide for creating and managing processing pipelines in the settings UI**
- Creating and editing pipeline steps
- Using variables ({input_text}, {original_text}, {target_language})
- Conditional execution and pipeline termination
- Document classification and branching
- Best practices and troubleshooting

---

## 🏗️ System Architecture

### [Architecture Overview](ARCHITECTURE.md)
System design, components, and data flow
- Modular pipeline architecture
- Document processing workflow
- Database schema overview
- Security and privacy considerations

### [Database Documentation](DATABASE.md)
Database schema and data models
- Table structures
- Relationships
- Query patterns
- Migrations

---

## 🔧 Technical References

### [Pipeline Variables Reference](PIPELINE_VARIABLES.md)
Complete reference for pipeline context variables
- Core variables: `{input_text}`, `{original_text}`, `{target_language}`, `{document_type}`
- Variable availability and lifecycle
- Usage examples and patterns
- Security considerations (PII handling)

### [API Reference](API.md)
REST API endpoints and usage
- Upload endpoints
- Processing endpoints
- Settings management
- Pipeline configuration
- Authentication endpoints

### [Configuration Reference](CONFIGURATION.md)
System configuration and settings
- Environment variables
- Feature flags
- Pipeline configuration
- Database settings

### [Optimized PII Filter](OPTIMIZED_PII_FILTER.md)
Advanced PII removal implementation
- Performance optimizations
- Pattern matching
- Entity recognition improvements
- spaCy NER integration

---

## 🚀 Deployment & Operations

### [Deployment Guide](DEPLOYMENT.md)
Production deployment procedures
- Railway deployment
- Environment configuration
- Database setup
- Troubleshooting

### [Railway Deployment Guide](RAILWAY_DEPLOYMENT_GUIDE.md)
Detailed Railway-specific deployment
- Service configuration
- Environment variables
- PostgreSQL setup
- Monitoring and logs

### [Development Setup](DEVELOPMENT.md)
Local development environment
- Prerequisites
- Installation steps
- Running locally
- Testing
- CI/CD with GitHub Actions
- Self-hosted ARC runners on Kubernetes

### [Testing Guide](TESTING.md)
Testing strategies and best practices
- Unit testing
- Integration testing
- E2E testing
- Test coverage

### [Monitoring & Troubleshooting](MONITORING_TROUBLESHOOTING.md)
System monitoring and debugging
- Performance monitoring
- Error tracking
- Log analysis
- Common issues and solutions

---

## ⚙️ Infrastructure & Performance

### [Worker Scaling](WORKER_SCALING.md)
Worker configuration and scaling strategies
- Concurrency settings
- Resource allocation
- Performance tuning

### [Concurrency vs Replicas](CONCURRENCY_VS_REPLICAS.md)
Understanding worker concurrency and service replicas
- Concurrency configuration
- Replica scaling
- Trade-offs and recommendations

### [RAM Optimization](RAM_OPTIMIZATION.md)
Memory usage optimization
- Memory profiling
- Optimization strategies
- Resource limits

### [Queue vs Active Tasks](QUEUE_VS_ACTIVE_TASKS.md)
Understanding task queuing and active task limits
- Queue management
- Active task configuration
- Performance implications

### [Feature Flags](FEATURE_FLAGS.md)
Feature flag system and usage
- Available feature flags
- Configuration
- Runtime behavior

---

## 🔐 Security & Privacy

### [Authentication Implementation](AUTHENTICATION_IMPLEMENTATION_SUMMARY.md)
Complete authentication system overview
- JWT-based authentication
- Role-based access control (RBAC)
- API key management
- Audit logging

### [Admin User Setup](ADMIN_USER_SETUP.md)
Creating and managing admin users
- Initial admin creation
- User management
- Password policies

### [Migration Guide](MIGRATION_GUIDE.md)
Database migration for authentication system
- Migration steps
- Verification procedures
- Troubleshooting

### [Deployment with Authentication](DEPLOYMENT_AUTH.md)
Deploying the authentication system
- Environment variables
- Production deployment
- Security considerations

### [PII Removal Toggle](PII_REMOVAL_TOGGLE.md)
Global PII removal configuration
- Enabling/disabling PII filtering
- Configuration management
- Testing procedures

### [Data Retention Policy](DATA_RETENTION.md)
Document and data retention rules
- Default retention periods (24 hours)
- Automatic cleanup jobs
- GDPR compliance
- Custom retention configuration

---

## 🔍 Features

### Token Tracking
**File:** [TOKEN_TRACKING.md](TOKEN_TRACKING.md)

Comprehensive token usage tracking and cost analysis
- Per-step token tracking
- Cost calculation
- Usage analytics
- Optimization recommendations

---

## 📦 Archive

Historical, planning, and implementation-specific documentation:

**Planning & Analysis:**
- [Phase 2 Summary](archive/PHASE_2_SUMMARY.md) - Phase 2 implementation summary
- [Phase 3 Plan](archive/PHASE3_PLAN.md) - Security & compliance planning
- [Architecture Assessment](archive/ARCHITECTURE_ASSESSMENT.md) - Architectural analysis
- [Refactoring Notes](archive/REFACTORING_NOTES.md) - Code refactoring documentation

**Implementation Guides:**
- [Implementation Checklists](archive/IMPLEMENTATION_CHECKLIST.md) - Feature implementation checklists
- [Frontend Integration Plans](archive/FRONTEND_INTEGRATION_ULTRAPLAN.md) - Frontend integration planning
- [Pipeline Termination Implementation](archive/PIPELINE_TERMINATION.md) - Pipeline termination feature
- [Frontend Termination Guide](archive/FRONTEND_TERMINATION_GUIDE.md) - Frontend termination UI

**Technical Investigations:**
- [Redis Cleanup Analysis](archive/REDIS_CLEANUP_ANALYSIS.md) - Redis cleanup investigation
- [Redis Diagnostic Results](archive/REDIS_DIAGNOSTIC_RESULTS.md) - Redis diagnostics
- [Phase Aware Ordering](archive/PHASE_AWARE_ORDERING.md) - Pipeline phase ordering
- [Type Checking](archive/TYPE_CHECKING.md) - Type checking implementation

**Legacy Documentation:**
- [Legacy Cleanup Summary](archive/LEGACY_CLEANUP_COMPLETE.md) - Previous cleanup documentation
- [Privacy Filter (Basic)](archive/PRIVACY_FILTER.md) - Basic privacy filter (superseded by OPTIMIZED_PII_FILTER.md)

---

## 🎯 Quick Start

### For Users
1. **[Pipeline User Guide](PIPELINE_USER_GUIDE.md)** - Learn to create and manage pipelines
2. **[Architecture Overview](ARCHITECTURE.md)** - Understand how the system works
3. **[Data Retention Policy](DATA_RETENTION.md)** - Know how long your data is stored

### For Developers
1. **[Development Setup](DEVELOPMENT.md)** - Set up local environment
2. **[API Reference](API.md)** - Understand the API endpoints
3. **[Database Documentation](DATABASE.md)** - Learn the data model
4. **[Pipeline Variables Reference](PIPELINE_VARIABLES.md)** - Master the pipeline system
5. **[Authentication Implementation](AUTHENTICATION_IMPLEMENTATION_SUMMARY.md)** - Authentication system

### For DevOps
1. **[Deployment Guide](DEPLOYMENT.md)** - Deploy to production
2. **[Railway Deployment Guide](RAILWAY_DEPLOYMENT_GUIDE.md)** - Railway-specific setup
3. **[Migration Guide](MIGRATION_GUIDE.md)** - Database migrations
4. **[Worker Scaling](WORKER_SCALING.md)** - Configure worker scaling
5. **[Data Retention Policy](DATA_RETENTION.md)** - Configure retention policies

---

## 📝 Document Types

| Icon | Type | Purpose |
|------|------|---------|
| 📘 | User Guide | End-user documentation |
| 🏗️ | Architecture | System design and structure |
| 🔧 | Technical Reference | Developer documentation |
| 🚀 | Operations | Deployment and maintenance |
| 🔐 | Security | Privacy and compliance |
| 🔍 | Features | Feature-specific docs |
| 📦 | Archive | Historical/deprecated docs |

---

## 🔄 Recently Updated

- **2025-10-28**: Major documentation cleanup - organized 43 docs into 26 active + 17 archived
- **2025-10-28**: Added authentication system documentation (AUTHENTICATION_IMPLEMENTATION_SUMMARY.md, ADMIN_USER_SETUP.md, MIGRATION_GUIDE.md)
- **2025-10-28**: Added Infrastructure & Performance section with scaling and optimization guides
- **2025-10-28**: Archived legacy planning and analysis documents (Phase 2/3, Redis diagnostics, refactoring notes)
- **2025-10-27**: Added database migration guide for authentication system
- **2025-10-24**: Added authentication deployment documentation
- **2025-10-14**: Added CI/CD and ARC runner documentation to DEVELOPMENT.md and DEPLOYMENT.md
- **2025-01-09**: Created comprehensive Pipeline User Guide and reorganized documentation structure

---

## 🤝 Contributing

To add or update documentation:

1. Follow the appropriate template for your document type
2. Place in the correct category folder
3. Update this index
4. Submit pull request with clear description

### Documentation Standards

- **Use Markdown** for all documentation
- **Include code examples** where appropriate
- **Add diagrams** for complex concepts (use Mermaid or ASCII)
- **Keep language clear** and avoid jargon
- **Update INDEX.md** when adding new docs
- **Version documentation** with dates

---

## 📧 Support

- **GitHub Issues**: Bug reports and feature requests
- **Development Team**: Technical support and questions
- **Documentation Issues**: Report errors or suggest improvements

---

**Last Updated:** October 2025
**Maintained by:** DocTranslator Team
