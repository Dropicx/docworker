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

### [Privacy Filter](PRIVACY_FILTER.md)
PII detection and removal system
- spaCy NER integration
- Entity types detected
- Configuration options

### [Optimized PII Filter](OPTIMIZED_PII_FILTER.md)
Advanced PII removal implementation
- Performance optimizations
- Pattern matching
- Entity recognition improvements

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

---

## 🔐 Security & Privacy

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

Historical and implementation-specific documentation:
- [Implementation Checklists](archive/IMPLEMENTATION_CHECKLIST.md)
- [Frontend Integration Plans](archive/FRONTEND_INTEGRATION_ULTRAPLAN.md)
- [Pipeline Termination Implementation](archive/PIPELINE_TERMINATION.md)
- [Frontend Termination Guide](archive/FRONTEND_TERMINATION_GUIDE.md)
- [Legacy Cleanup Summary](archive/LEGACY_CLEANUP_COMPLETE.md)

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

### For DevOps
1. **[Deployment Guide](DEPLOYMENT.md)** - Deploy to production
2. **[Railway Deployment Guide](RAILWAY_DEPLOYMENT_GUIDE.md)** - Railway-specific setup
3. **[Data Retention Policy](DATA_RETENTION.md)** - Configure retention policies

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

- **2025-10-14**: Added CI/CD and ARC runner documentation to DEVELOPMENT.md and DEPLOYMENT.md
- **2025-10-14**: Enhanced README with self-hosted runners information
- **2025-01-09**: Created comprehensive Pipeline User Guide
- **2025-01-09**: Reorganized documentation structure
- **2025-01-09**: Moved technical implementation docs to archive
- **2024-10-09**: Added data retention documentation
- **2024-10-09**: Updated architecture documentation

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

**Last Updated:** January 2025
**Maintained by:** DocTranslator Team
