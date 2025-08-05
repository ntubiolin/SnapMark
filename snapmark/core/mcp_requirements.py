"""MCP dependency management and validation."""

import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


def check_mcp_dependencies() -> Dict[str, any]:
    """Check availability of MCP-related dependencies.
    
    Returns:
        Dictionary with dependency status and error messages
    """
    results = {
        'mcp_use_available': False,
        'langchain_openai_available': False,
        'openai_configured': False,
        'errors': [],
        'warnings': []
    }
    
    # Check mcp-use
    try:
        import mcp_use
        results['mcp_use_available'] = True
        logger.debug("mcp-use library is available")
    except ImportError as e:
        results['errors'].append(f"mcp-use not available: {e}")
        logger.warning(f"mcp-use import failed: {e}")
    
    # Check langchain-openai
    try:
        import langchain_openai
        results['langchain_openai_available'] = True
        logger.debug("langchain-openai library is available")
    except ImportError as e:
        results['errors'].append(f"langchain-openai not available: {e}")
        logger.warning(f"langchain-openai import failed: {e}")
    
    # Check OpenAI configuration
    try:
        from ..config import config
        vlm_config = config.get('vlm', {})
        if vlm_config.get('provider') == 'openai' and vlm_config.get('openai_api_key'):
            results['openai_configured'] = True
            logger.debug("OpenAI is configured")
        else:
            results['warnings'].append("OpenAI not configured - intelligent agent features will be limited")
    except Exception as e:
        results['warnings'].append(f"Could not check OpenAI configuration: {e}")
    
    return results


def get_missing_dependencies() -> List[str]:
    """Get list of missing dependencies needed for full MCP functionality.
    
    Returns:
        List of missing package names
    """
    missing = []
    
    try:
        import mcp_use
    except ImportError:
        missing.append("mcp-use")
    
    try:
        import langchain_openai
    except ImportError:
        missing.append("langchain-openai")
    
    return missing


def validate_mcp_setup() -> Tuple[bool, List[str]]:
    """Validate complete MCP setup.
    
    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []
    
    # Check dependencies
    missing_deps = get_missing_dependencies()
    if missing_deps:
        issues.append(f"Missing dependencies: {', '.join(missing_deps)}")
    
    # Check configuration
    try:
        from ..config import config
        mcp_config = config.get('mcp', {})
        if not mcp_config.get('enabled', False):
            issues.append("MCP is not enabled in configuration")
        
        vlm_config = config.get('vlm', {})
        if vlm_config.get('provider') != 'openai' or not vlm_config.get('openai_api_key'):
            issues.append("OpenAI not configured - intelligent features unavailable")
    except Exception as e:
        issues.append(f"Configuration validation failed: {e}")
    
    return len(issues) == 0, issues


def log_mcp_status():
    """Log current MCP integration status."""
    status = check_mcp_dependencies()
    
    if status['mcp_use_available'] and status['langchain_openai_available']:
        if status['openai_configured']:
            logger.info("✅ MCP integration fully available with intelligent agent support")
        else:
            logger.info("⚠️  MCP integration available but OpenAI not configured - limited functionality")
    else:
        logger.warning("❌ MCP integration limited due to missing dependencies")
        for error in status['errors']:
            logger.warning(f"  - {error}")
    
    for warning in status['warnings']:
        logger.info(f"  ⚠️  {warning}")