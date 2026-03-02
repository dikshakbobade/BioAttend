"""
Fingerprint Verification Agent
Captures fingerprint from USB scanner and sends to backend for verification.
Supports multiple vendor SDKs: Mantra MFS100, SecuGen, ZKTeco
"""

import os
import sys
import time
import base64
import logging
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple
from datetime import datetime
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class AgentConfig:
    backend_url: str
    device_id: str
    api_key: str
    vendor: str  # 'mantra', 'secugen', 'zkteco', 'mock'
    scan_timeout: int = 10  # seconds
    retry_attempts: int = 3
    cooldown_seconds: int = 5
    
    @classmethod
    def from_env(cls) -> 'AgentConfig':
        return cls(
            backend_url=os.getenv('BACKEND_URL', 'http://localhost:8000'),
            device_id=os.getenv('DEVICE_ID', 'FP-001'),
            api_key=os.getenv('API_KEY', ''),
            vendor=os.getenv('FINGERPRINT_VENDOR', 'mock').lower(),
            scan_timeout=int(os.getenv('SCAN_TIMEOUT', '10')),
            retry_attempts=int(os.getenv('RETRY_ATTEMPTS', '3')),
            cooldown_seconds=int(os.getenv('COOLDOWN_SECONDS', '5'))
        )


# =============================================================================
# Abstract Scanner Interface
# =============================================================================

class FingerprintScanner(ABC):
    """Abstract base class for fingerprint scanner implementations."""
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the scanner device."""
        pass
    
    @abstractmethod
    def capture(self, timeout: int = 10) -> Tuple[Optional[bytes], int]:
        """
        Capture fingerprint template.
        Returns: (template_bytes, quality_score) or (None, 0) on failure
        """
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Release scanner resources."""
        pass
    
    @abstractmethod
    def is_finger_present(self) -> bool:
        """Check if finger is on scanner."""
        pass


# =============================================================================
# Mantra MFS100 Implementation
# =============================================================================

class MantraScanner(FingerprintScanner):
    """
    Mantra MFS100 fingerprint scanner implementation.
    Requires: MFS100 SDK installed, libmfs100.so available
    
    Installation:
    1. Download MFS100 Linux SDK from Mantra website
    2. Install: sudo dpkg -i MFS100-*.deb
    3. Configure udev rules for device access
    """
    
    def __init__(self):
        self.device = None
        self.initialized = False
        
    def initialize(self) -> bool:
        try:
            # Import Mantra SDK (install separately)
            # from mantra import MFS100
            # self.device = MFS100()
            # result = self.device.Init()
            # self.initialized = result == 0
            
            logger.warning("Mantra SDK not installed. Install MFS100 SDK first.")
            logger.info("For installation: https://download.mantratecapp.com/")
            return False
            
        except ImportError:
            logger.error("Mantra SDK not found. Please install MFS100 SDK.")
            return False
        except Exception as e:
            logger.error(f"Mantra initialization error: {e}")
            return False
    
    def capture(self, timeout: int = 10) -> Tuple[Optional[bytes], int]:
        if not self.initialized:
            return None, 0
            
        try:
            # Example Mantra SDK capture code:
            # result = self.device.AutoCapture(timeout * 1000)  # ms
            # if result.ErrorCode == 0:
            #     template = result.ISOTemplate  # ISO 19794-2 format
            #     quality = result.Quality
            #     return template, quality
            # return None, 0
            pass
        except Exception as e:
            logger.error(f"Mantra capture error: {e}")
            return None, 0
    
    def cleanup(self) -> None:
        if self.device:
            # self.device.Uninit()
            pass
    
    def is_finger_present(self) -> bool:
        if not self.initialized:
            return False
        # return self.device.IsFingerPresent()
        return False


# =============================================================================
# SecuGen Implementation
# =============================================================================

class SecuGenScanner(FingerprintScanner):
    """
    SecuGen Hamster Pro 20 implementation.
    Requires: SecuGen SDK installed
    
    Installation:
    1. Download SecuGen FDx SDK Pro for Linux
    2. Extract and run install script
    3. Configure USB permissions
    """
    
    def __init__(self):
        self.device = None
        self.initialized = False
        
    def initialize(self) -> bool:
        try:
            # Import SecuGen SDK
            # from pysgfplib import SGFPLib
            # self.device = SGFPLib()
            # error = self.device.Init(SGFPLib.SG_DEV_AUTO)
            # if error == SGFPLib.SGFDX_ERROR_NONE:
            #     self.device.OpenDevice(0)
            #     self.initialized = True
            
            logger.warning("SecuGen SDK not installed. Install FDx SDK first.")
            return False
            
        except ImportError:
            logger.error("SecuGen SDK not found.")
            return False
        except Exception as e:
            logger.error(f"SecuGen initialization error: {e}")
            return False
    
    def capture(self, timeout: int = 10) -> Tuple[Optional[bytes], int]:
        if not self.initialized:
            return None, 0
            
        try:
            # Example SecuGen capture:
            # image_buffer = bytearray(self.device.GetImageWidth() * self.device.GetImageHeight())
            # self.device.GetImageEx(image_buffer, timeout * 1000)
            # 
            # template = bytearray(400)  # Max template size
            # quality = [0]
            # self.device.CreateTemplate(image_buffer, template, quality)
            # 
            # return bytes(template), quality[0]
            pass
        except Exception as e:
            logger.error(f"SecuGen capture error: {e}")
            return None, 0
    
    def cleanup(self) -> None:
        if self.device:
            # self.device.CloseDevice()
            pass
    
    def is_finger_present(self) -> bool:
        return False


# =============================================================================
# ZKTeco Implementation
# =============================================================================

class ZKTecoScanner(FingerprintScanner):
    """
    ZKTeco ZK4500/ZK9500 implementation.
    Requires: ZKFinger SDK installed
    
    Installation:
    1. Download ZKFinger SDK from ZKTeco
    2. Install libzkfp.so to /usr/lib
    3. Configure udev rules
    """
    
    def __init__(self):
        self.handle = None
        self.db_handle = None
        self.initialized = False
        
    def initialize(self) -> bool:
        try:
            # Import ZKTeco SDK
            # import zkfp
            # ret = zkfp.Init()
            # if ret == zkfp.CYCFP_ERR_OK:
            #     device_count = zkfp.GetDeviceCount()
            #     if device_count > 0:
            #         self.handle = zkfp.OpenDevice(0)
            #         self.db_handle = zkfp.DBInit()
            #         self.initialized = True
            
            logger.warning("ZKTeco SDK not installed. Install ZKFinger SDK first.")
            return False
            
        except ImportError:
            logger.error("ZKTeco SDK not found.")
            return False
        except Exception as e:
            logger.error(f"ZKTeco initialization error: {e}")
            return False
    
    def capture(self, timeout: int = 10) -> Tuple[Optional[bytes], int]:
        if not self.initialized:
            return None, 0
            
        try:
            # Example ZKTeco capture:
            # image = zkfp.AcquireFingerprint(self.handle, timeout * 1000)
            # if image:
            #     template, quality = zkfp.ExtractTemplate(self.handle, image)
            #     return template, quality
            pass
        except Exception as e:
            logger.error(f"ZKTeco capture error: {e}")
            return None, 0
    
    def cleanup(self) -> None:
        if self.handle:
            # zkfp.CloseDevice(self.handle)
            # zkfp.Terminate()
            pass
    
    def is_finger_present(self) -> bool:
        return False


# =============================================================================
# Mock Scanner (for testing)
# =============================================================================

class MockScanner(FingerprintScanner):
    """Mock scanner for testing without hardware."""
    
    def __init__(self):
        self.initialized = False
        self._finger_present = False
        
    def initialize(self) -> bool:
        logger.info("Mock scanner initialized (for testing only)")
        self.initialized = True
        return True
    
    def capture(self, timeout: int = 10) -> Tuple[Optional[bytes], int]:
        """Generate a mock template for testing."""
        import hashlib
        import random
        
        # Simulate capture delay
        time.sleep(1)
        
        # Generate deterministic mock template based on time
        seed = f"mock_fp_{datetime.now().strftime('%Y%m%d%H')}"
        mock_template = hashlib.sha256(seed.encode()).digest() * 12  # ~384 bytes
        quality = random.randint(70, 95)
        
        logger.info(f"Mock capture complete. Quality: {quality}")
        return mock_template, quality
    
    def cleanup(self) -> None:
        logger.info("Mock scanner cleanup")
    
    def is_finger_present(self) -> bool:
        return True  # Always ready in mock mode


# =============================================================================
# Scanner Factory
# =============================================================================

def create_scanner(vendor: str) -> FingerprintScanner:
    """Factory function to create appropriate scanner instance."""
    scanners = {
        'mantra': MantraScanner,
        'secugen': SecuGenScanner,
        'zkteco': ZKTecoScanner,
        'mock': MockScanner
    }
    
    scanner_class = scanners.get(vendor.lower())
    if not scanner_class:
        raise ValueError(f"Unknown vendor: {vendor}. Supported: {list(scanners.keys())}")
    
    return scanner_class()


# =============================================================================
# Fingerprint Agent
# =============================================================================

class FingerprintAgent:
    """Main agent class that coordinates scanner and backend communication."""
    
    def __init__(self, config: AgentConfig):
        self.config = config
        self.scanner: Optional[FingerprintScanner] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.running = False
        self.last_success_time: Optional[datetime] = None
        
    async def initialize(self) -> bool:
        """Initialize scanner and HTTP client."""
        try:
            # Create scanner instance
            self.scanner = create_scanner(self.config.vendor)
            if not self.scanner.initialize():
                logger.error("Failed to initialize scanner")
                return False
            
            # Create HTTP client with retry
            self.http_client = httpx.AsyncClient(
                base_url=self.config.backend_url,
                headers={
                    'X-API-Key': self.config.api_key,
                    'X-Device-ID': self.config.device_id,
                    'Content-Type': 'application/json'
                },
                timeout=30.0
            )
            
            # Test backend connection
            try:
                response = await self.http_client.get('/health')
                if response.status_code != 200:
                    logger.warning("Backend health check failed")
            except Exception as e:
                logger.warning(f"Backend not reachable: {e}")
            
            logger.info(f"Agent initialized: {self.config.device_id} ({self.config.vendor})")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    async def verify_fingerprint(self, template: bytes, quality: int) -> dict:
        """Send fingerprint to backend for verification."""
        template_b64 = base64.b64encode(template).decode('utf-8')
        
        payload = {
            'fingerprint_template': template_b64,
            'quality_score': quality,
            'device_id': self.config.device_id,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        for attempt in range(self.config.retry_attempts):
            try:
                response = await self.http_client.post(
                    '/api/v1/biometric/fingerprint/verify',
                    json=payload
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 401:
                    logger.error("Authentication failed - check API key")
                    return {'success': False, 'message': 'Authentication failed'}
                elif response.status_code == 429:
                    logger.warning("Rate limited - waiting...")
                    await asyncio.sleep(5)
                else:
                    logger.warning(f"Verification failed: {response.status_code}")
                    
            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Request error: {e}")
            
            if attempt < self.config.retry_attempts - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return {'success': False, 'message': 'Verification request failed'}
    
    def _in_cooldown(self) -> bool:
        """Check if we're in cooldown period after successful scan."""
        if self.last_success_time is None:
            return False
        elapsed = (datetime.now() - self.last_success_time).seconds
        return elapsed < self.config.cooldown_seconds
    
    async def run_detection_loop(self, display_result: bool = True):
        """Main loop for continuous fingerprint detection."""
        self.running = True
        logger.info("Starting fingerprint detection loop...")
        logger.info("Press Ctrl+C to stop")
        
        while self.running:
            try:
                # Check cooldown
                if self._in_cooldown():
                    await asyncio.sleep(0.5)
                    continue
                
                # Check for finger presence (if supported)
                if hasattr(self.scanner, 'is_finger_present'):
                    if not self.scanner.is_finger_present():
                        await asyncio.sleep(0.3)
                        continue
                
                # Capture fingerprint
                logger.info("Finger detected - capturing...")
                template, quality = self.scanner.capture(self.config.scan_timeout)
                
                if template is None:
                    logger.warning("Capture failed - no template")
                    await asyncio.sleep(1)
                    continue
                
                if quality < 50:
                    logger.warning(f"Low quality scan: {quality}. Please try again.")
                    await asyncio.sleep(1)
                    continue
                
                logger.info(f"Template captured. Quality: {quality}")
                
                # Verify with backend
                result = await self.verify_fingerprint(template, quality)
                
                if display_result:
                    self._display_result(result)
                
                if result.get('success'):
                    self.last_success_time = datetime.now()
                    logger.info(f"Cooldown: {self.config.cooldown_seconds}s")
                
                await asyncio.sleep(1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Detection loop error: {e}")
                await asyncio.sleep(2)
        
        logger.info("Detection loop stopped")
    
    def _display_result(self, result: dict):
        """Display verification result."""
        if result.get('success'):
            employee = result.get('employee', {})
            action = result.get('attendance_action', 'unknown')
            confidence = result.get('confidence_score', 0)
            
            print("\n" + "=" * 50)
            print("✓ VERIFICATION SUCCESSFUL")
            print("=" * 50)
            print(f"  Employee: {employee.get('full_name', 'Unknown')}")
            print(f"  ID: {employee.get('employee_code', 'N/A')}")
            print(f"  Department: {employee.get('department', 'N/A')}")
            print(f"  Action: {action.upper()}")
            print(f"  Confidence: {confidence:.1%}")
            print(f"  Time: {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 50 + "\n")
        else:
            print("\n" + "-" * 50)
            print("✗ VERIFICATION FAILED")
            print("-" * 50)
            print(f"  Reason: {result.get('message', 'Unknown error')}")
            print("-" * 50 + "\n")
    
    async def cleanup(self):
        """Cleanup resources."""
        self.running = False
        if self.scanner:
            self.scanner.cleanup()
        if self.http_client:
            await self.http_client.aclose()
        logger.info("Agent cleanup complete")


# =============================================================================
# Enrollment Mode
# =============================================================================

async def enrollment_mode(config: AgentConfig, employee_id: int, num_samples: int = 3):
    """
    Enrollment mode to capture multiple fingerprint samples.
    Sends best quality template to backend for registration.
    """
    scanner = create_scanner(config.vendor)
    if not scanner.initialize():
        logger.error("Scanner initialization failed")
        return False
    
    templates = []
    qualities = []
    
    print(f"\n{'='*50}")
    print(f"FINGERPRINT ENROLLMENT - Employee ID: {employee_id}")
    print(f"Please scan finger {num_samples} times")
    print(f"{'='*50}\n")
    
    for i in range(num_samples):
        print(f"Scan {i+1}/{num_samples}: Place finger on scanner...")
        
        # Wait for finger
        while not scanner.is_finger_present():
            time.sleep(0.3)
        
        template, quality = scanner.capture()
        
        if template and quality >= 50:
            templates.append(template)
            qualities.append(quality)
            print(f"  ✓ Captured. Quality: {quality}")
            
            if i < num_samples - 1:
                print("  Remove finger...")
                time.sleep(1)
        else:
            print(f"  ✗ Failed. Please try again.")
            i -= 1  # Retry this sample
    
    scanner.cleanup()
    
    if not templates:
        logger.error("No valid templates captured")
        return False
    
    # Select best quality template
    best_idx = qualities.index(max(qualities))
    best_template = templates[best_idx]
    best_quality = qualities[best_idx]
    
    print(f"\nBest template quality: {best_quality}")
    print("Registering with backend...")
    
    # Send to backend
    async with httpx.AsyncClient(
        base_url=config.backend_url,
        headers={
            'X-API-Key': config.api_key,
            'Content-Type': 'application/json'
        }
    ) as client:
        response = await client.post(
            f'/api/v1/employees/{employee_id}/biometric',
            json={
                'biometric_type': 'fingerprint',
                'template_data': base64.b64encode(best_template).decode(),
                'quality_score': best_quality
            }
        )
        
        if response.status_code == 200:
            print("✓ Enrollment successful!")
            return True
        else:
            print(f"✗ Enrollment failed: {response.text}")
            return False


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fingerprint Verification Agent')
    parser.add_argument('--enroll', type=int, help='Enroll employee ID')
    parser.add_argument('--samples', type=int, default=3, help='Enrollment samples')
    parser.add_argument('--vendor', type=str, help='Override vendor from env')
    args = parser.parse_args()
    
    config = AgentConfig.from_env()
    if args.vendor:
        config.vendor = args.vendor
    
    if args.enroll:
        # Enrollment mode
        await enrollment_mode(config, args.enroll, args.samples)
    else:
        # Verification mode
        agent = FingerprintAgent(config)
        
        if not await agent.initialize():
            logger.error("Agent initialization failed")
            sys.exit(1)
        
        try:
            await agent.run_detection_loop()
        except KeyboardInterrupt:
            logger.info("Stopping agent...")
        finally:
            await agent.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
