# Velocity LIMS

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Django 5.0](https://img.shields.io/badge/django-5.0-green.svg)](https://djangoproject.com/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-supported-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/license-Open%20Source-brightgreen.svg)](LICENSE)

> A modern, Python-powered Laboratory Information Management System designed for high-throughput laboratories, built by seasoned LIMS professionals for the global scientific community.

![Velocity LIMS Hero](screen_11_scripts.png)

## 🚀 Overview

Velocity LIMS is a lightweight, high-performance Laboratory Information Management System built from the ground up with modern web technologies. Unlike traditional LIMS solutions, Velocity prioritizes speed, simplicity, and developer experience while maintaining enterprise-grade functionality.

### ✨ Key Features

- **🏃‍♂️ Built for Speed**: Sub-50ms typical API response times with direct PostgreSQL queries
- **🔒 Enterprise Security**: Custom RBAC system with session-based authentication
- **📱 Modern Interface**: Responsive web UI with real-time updates via WebSockets
- **🔧 Developer Friendly**: Clean Python/Django codebase with extensive customization options
- **💰 Zero Cost**: Completely free and open source - [learn why](splash/why-free.html)
- **☁️ Cloud Ready**: Optimized for AWS deployment with horizontal scaling support

### 📊 Performance Metrics

- **100M+** Requisitions tracked in production
- **300M+** Specimens indexed and managed  
- **Sub-50ms** typical API read operations
- **WebSocket-ready** for real-time laboratory updates

## 🏗️ Architecture

Velocity LIMS follows a modern, performance-focused architecture:

- **Backend**: Django 5.0 with direct PostgreSQL connections via psycopg
- **Database**: PostgreSQL with `velocity.*` schema organization
- **Frontend**: Custom JavaScript with AJAX-based communication
- **Authentication**: Session-based RBAC with granular permissions
- **Deployment**: Docker-ready with AWS optimization

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Web Framework | Django 5.0 | Core application framework |
| Database | PostgreSQL | Primary data storage with `velocity.*` schema |
| Database Driver | psycopg (direct) | High-performance database connections |
| Authentication | Custom RBAC | Role-based access control system |
| Frontend | Vanilla JS + AJAX | Lightweight, fast user interface |
| Real-time | WebSockets | Live updates and notifications |

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- PostgreSQL 12+
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/brianbgriffiths/velocity-lims.git
   cd velocity-lims
   ```

2. **Install dependencies**
   ```bash
   pip install django psycopg2-binary
   ```

3. **Configure database settings**
   
   Edit `settings/settings.py` to configure your PostgreSQL connection:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'velocity_lims',
           'USER': 'your_db_user',
           'PASSWORD': 'your_db_password',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```

4. **Initialize the database**
   ```bash
   python manage.py migrate
   ```

5. **Start the development server**
   ```bash
   python manage.py runserver
   ```

6. **Access the application**
   
   Navigate to `http://localhost:8000` in your web browser.

## 📋 Core Modules

Velocity LIMS is organized into focused modules:

| Module | Description | Status |
|--------|-------------|--------|
| **Authentication** | User login/logout and session management | ✅ Active |
| **Roles & Permissions** | RBAC system with granular access control | ✅ Active |
| **Samples** | Sample tracking and management | ✅ Active |
| **Containers** | Laboratory container and plate management | ✅ Active |
| **Assays** | Test and assay configuration | ✅ Active |
| **Workflows** | Laboratory process automation | ✅ Active |
| **Specimens** | Biological specimen tracking | ✅ Active |
| **Protocols** | Standard operating procedures | 🔧 Configurable |
| **Automations** | Laboratory equipment integration | 🔧 Configurable |
| **Organizations** | Multi-tenant organization support | 🔧 Configurable |

## 🔧 Configuration


### Database Schema

The system uses a `velocity.*` schema prefix for organization:

- `velocity.accounts` - User account information
- `velocity.roles` - Role definitions with JSON permissions
- `velocity.specimens` - Sample and specimen tracking
- `velocity.containers` - Laboratory containers and plates
- `velocity.workflows` - Process definitions and steps


## 🔒 Security & RBAC

Velocity LIMS implements a comprehensive Role-Based Access Control system:

### Authentication
- Session-based authentication with secure token management
- `@login_required` decorator for protected views
- Custom user management with flexible permission assignment

### Authorization
```python
# Check user permissions in views
from settings.views import has_permission

@login_required
def secure_view(request):
    if not has_permission(request, 'manage_samples'):
        return JsonResponse({'error': 'Insufficient permissions'})
    # ... view logic
```

### Permission System
- Granular permissions stored as JSON in role definitions
- Dynamic permission checking with session caching
- Support for both role-based and direct permission assignment

## 🧪 Laboratory Features

### Sample Management
- Full sample lifecycle tracking from collection to disposal
- Barcode integration and label printing support
- Chain of custody documentation
- Quality control and batch management

### Container Management  
- Plate and tube tracking with position management
- Volume and aliquot tracking
- Freezer and storage location mapping
- Automated plate layout generation

### Workflow Automation
- Configurable laboratory processes and protocols
- Step-by-step guidance with validation
- Integration points for laboratory equipment
- Real-time status updates via WebSockets

### Assay Management
- Test configuration and protocol management
- Result capture and validation
- Quality control integration
- Regulatory compliance tracking

## 🏢 Production Deployment

### AWS Deployment
Velocity LIMS is optimized for AWS deployment:

```bash
# Example AWS configuration
SERVER_URL = "https://demo.velocitylims.com"
ALLOWED_HOSTS = ["*.velocitylims.com", "your-domain.com"]
```

### Performance Optimization
- Direct psycopg connections bypass Django ORM overhead
- Session-based authentication reduces database queries
- Efficient SQL queries with proper indexing
- WebSocket support for real-time updates without polling

### Scaling Considerations
- Horizontal scaling support with session store externalization
- Database connection pooling for high concurrency
- Static asset optimization and CDN integration
- Background task processing for heavy operations

## 🤝 Contributing

We welcome contributions from the laboratory and software development communities!

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes following the existing patterns
4. Test thoroughly with the built-in tools
5. Submit a pull request with detailed description

### Code Style
- Follow existing Django and Python conventions
- Use the custom `pylims.py` utilities for database connections
- Implement proper error handling with `pylims_ui.error()`
- Add appropriate `@login_required` and permission checks

### Testing
```bash
# Run the test suite
python manage.py test

# Check for permission issues
python check_permissions.py

# Validate container relationships  
python check_containers.py
```

## 📚 Documentation

- **[API Documentation](docs/api.md)** - REST API reference
- **[Module Development](docs/modules.md)** - Creating custom modules
- **[Database Schema](db_schema_map.json)** - Complete schema reference
- **[Deployment Guide](docs/deployment.md)** - Production deployment
- **[Screenshots & Features](splash/)** - Visual feature overview

## 🆘 Support

- **GitHub Issues**: [Report bugs and request features](https://github.com/brianbgriffiths/velocity-lims/issues)
- **Documentation**: Check the `docs/` directory for detailed guides
- **Community**: Join our discussions in GitHub Discussions

## 📄 License

Velocity LIMS is open source software. See [LICENSE](LICENSE) for details.

## 🏆 Credits

Built with ❤️ by seasoned LIMS professionals for the global scientific community. 

**Why is it free?** [Learn about our mission](https://velocitylims.com/why-free.html) to democratize laboratory software.

---

## 🔗 Links

- **Live Demo**: [https://demo.velocitylims.com](https://demo.velocitylims.com)
- **Website**: [https://velocitylims.com](https://velocitylims.com) 
- **GitHub**: [https://github.com/brianbgriffiths/velocity-lims](https://github.com/brianbgriffiths/velocity-lims)
