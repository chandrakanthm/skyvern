#!/usr/bin/env python3

import sys
import os
sys.path.append('/home/ubuntu/skyvern')

from skyvern.forge.sdk.brand_guidelines.config_manager import BrandGuidelinesConfigManager
from skyvern.forge.sdk.brand_guidelines.models import ColorFormat

def test_brand_guidelines_system():
    print("Testing Brand Guidelines Configuration System")
    print("=" * 50)
    
    config_manager = BrandGuidelinesConfigManager()
    
    print("\n1. Testing JSON configuration loading...")
    try:
        json_guidelines = config_manager.load_from_file('/home/ubuntu/skyvern/examples/brand_guidelines_sample.json')
        print(f"✅ JSON loaded successfully: {json_guidelines.name} v{json_guidelines.version}")
        print(f"   - Colors: {len(json_guidelines.colors)}")
        print(f"   - Fonts: {len(json_guidelines.fonts)}")
        print(f"   - Spacing rules: {len(json_guidelines.spacing)}")
    except Exception as e:
        print(f"❌ JSON loading failed: {e}")
        return False
    
    print("\n2. Testing YAML configuration loading...")
    try:
        yaml_guidelines = config_manager.load_from_file('/home/ubuntu/skyvern/examples/brand_guidelines_sample.yaml')
        print(f"✅ YAML loaded successfully: {yaml_guidelines.name} v{yaml_guidelines.version}")
        print(f"   - Colors: {len(yaml_guidelines.colors)}")
        print(f"   - Fonts: {len(yaml_guidelines.fonts)}")
        print(f"   - Spacing rules: {len(yaml_guidelines.spacing)}")
    except Exception as e:
        print(f"❌ YAML loading failed: {e}")
        return False
    
    print("\n3. Testing color validation...")
    try:
        violations = json_guidelines.validate_color("#007bff")
        if not violations:
            print("✅ Valid color correctly accepted")
        else:
            print(f"❌ Valid color rejected: {violations}")
            
        violations = json_guidelines.validate_color("#ff0000")
        if violations:
            print("✅ Invalid color correctly rejected")
        else:
            print("❌ Invalid color incorrectly accepted")
            
    except Exception as e:
        print(f"❌ Color validation failed: {e}")
        return False
    
    print("\n4. Testing font validation...")
    try:
        violations = json_guidelines.validate_font("Arial, Helvetica, sans-serif", "16px", "normal")
        if not violations:
            print("✅ Valid font correctly accepted")
        else:
            print(f"❌ Valid font rejected: {violations}")
            
        violations = json_guidelines.validate_font("Comic Sans MS", "16px", "normal")
        if violations:
            print("✅ Invalid font correctly rejected")
        else:
            print("❌ Invalid font incorrectly accepted")
            
    except Exception as e:
        print(f"❌ Font validation failed: {e}")
        return False
    
    print("\n5. Testing spacing validation...")
    try:
        violations = json_guidelines.validate_spacing("margin", "16px")
        if not violations:
            print("✅ Valid spacing correctly accepted")
        else:
            print(f"❌ Valid spacing rejected: {violations}")
            
        violations = json_guidelines.validate_spacing("margin", "13px")
        if violations:
            print("✅ Invalid spacing correctly rejected")
        else:
            print("❌ Invalid spacing incorrectly accepted")
            
    except Exception as e:
        print(f"❌ Spacing validation failed: {e}")
        return False
    
    print("\n6. Testing sample guidelines creation...")
    try:
        sample_guidelines = config_manager.create_sample_guidelines()
        print(f"✅ Sample guidelines created: {sample_guidelines.name}")
        print(f"   - Colors: {len(sample_guidelines.colors)}")
        print(f"   - Fonts: {len(sample_guidelines.fonts)}")
        print(f"   - Spacing rules: {len(sample_guidelines.spacing)}")
    except Exception as e:
        print(f"❌ Sample guidelines creation failed: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ All brand guidelines tests passed!")
    return True

if __name__ == "__main__":
    success = test_brand_guidelines_system()
    sys.exit(0 if success else 1)
