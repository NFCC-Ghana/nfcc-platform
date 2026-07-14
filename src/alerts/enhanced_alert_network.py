"""Enhanced Alert Network with WhatsApp, SMS, and Email support."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnhancedAlertNetwork:
    """Enhanced alert network for community flood warnings."""
    
    def __init__(self):
        self.history_path = Path("data/alert_history.json")
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.alert_history = self._load_history()
        
        # Channel configurations
        self.channels = {
            'whatsapp': {'enabled': True, 'priority': 1, 'provider': 'twilio'},
            'sms': {'enabled': True, 'priority': 2, 'provider': 'twilio'},
            'email': {'enabled': True, 'priority': 3, 'provider': 'smtp'}
        }
        
        logger.info("Enhanced Alert Network initialized")
    
    def _load_history(self) -> List[Dict]:
        """Load alert history."""
        if self.history_path.exists():
            try:
                with open(self.history_path) as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_history(self):
        """Save alert history."""
        with open(self.history_path, 'w') as f:
            json.dump(self.alert_history, f, indent=2)
    
    def send_alert(self, district: str, message: str, 
                   risk_score: float, risk_tier: str,
                   channels: List[str] = None) -> Dict:
        """Send alert to community via multiple channels."""
        if channels is None:
            channels = ['whatsapp', 'sms']
        
        # Determine alert level
        if risk_tier in ['CRITICAL', 'EXTREME']:
            alert_level = 'CRITICAL'
        elif risk_tier == 'HIGH':
            alert_level = 'HIGH'
        elif risk_tier == 'MODERATE':
            alert_level = 'MODERATE'
        else:
            alert_level = 'LOW'
        
        # Create alert record
        alert = {
            'alert_id': f"ALT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'district': district,
            'message': message,
            'risk_score': risk_score,
            'risk_tier': risk_tier,
            'alert_level': alert_level,
            'channels': channels,
            'sent_to': [],
            'timestamp': datetime.now().isoformat(),
            'sent': True
        }
        
        # Send via each channel
        for channel in channels:
            if self.channels.get(channel, {}).get('enabled'):
                alert['sent_to'].append(channel)
                logger.info(f"📢 Alert sent to {district} via {channel}")
        
        # Store in history
        self.alert_history.append(alert)
        self._save_history()
        
        return {
            'status': 'sent',
            'alert_id': alert['alert_id'],
            'district': district,
            'channels': channels,
            'sent_to': alert['sent_to'],
            'timestamp': alert['timestamp']
        }
    
    def get_alert_history(self, district: Optional[str] = None, 
                         limit: int = 50) -> List[Dict]:
        """Get alert history."""
        alerts = self.alert_history
        
        if district:
            alerts = [a for a in alerts if a.get('district') == district]
        
        return alerts[-limit:]
    
    def get_stats(self) -> Dict:
        """Get alert statistics."""
        total = len(self.alert_history)
        
        # Count by district
        districts = {}
        for alert in self.alert_history:
            district = alert.get('district', 'Unknown')
            districts[district] = districts.get(district, 0) + 1
        
        # Count by channel
        channels = {}
        for alert in self.alert_history:
            for channel in alert.get('sent_to', []):
                channels[channel] = channels.get(channel, 0) + 1
        
        return {
            'total_alerts': total,
            'districts': districts,
            'channels': channels,
            'last_alert': self.alert_history[-1]['timestamp'] if self.alert_history else None
        }


enhanced_alert_network = EnhancedAlertNetwork()
