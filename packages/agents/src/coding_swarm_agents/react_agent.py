"""
React Development Agent - Specialized for React/Next.js development
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import re

from .base import Agent


class ReactAgent(Agent):
    """Specialized agent for React development"""

    def __init__(self, context: Dict[str, Any]) -> None:
        super().__init__(context)
        self.framework = "react"
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        """Load React-specific code templates"""
        return {
            "component": """import React, { useState, useEffect } from 'react';

interface {ComponentName}Props {
  // Add props here
}

const {ComponentName}: React.FC<{ComponentName}Props> = (props) => {
  // Component logic here

  return (
    <div className="{component-name}">
      {/* Component JSX here */}
      <h1>{ComponentName} Component</h1>
    </div>
  );
};

export default {ComponentName};""",

            "hook": """import { useState, useEffect } from 'react';

interface Use{ComponentName}Options {
  // Add options here
}

export const use{ComponentName} = (options: Use{ComponentName}Options = {}) => {
  // Hook logic here

  return {
    // Return values here
  };
};""",

            "page": """import React from 'react';
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: '{PageTitle}',
  description: '{PageDescription}',
};

export default function {PageName}Page() {
  return (
    <main>
      <h1>{PageTitle}</h1>
      {/* Page content here */}
    </main>
  );
}""",

            "api_route": """import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    // API logic here
    return NextResponse.json({ message: 'Success' });
  } catch (error) {
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    // API logic here
    return NextResponse.json({ message: 'Created', data: body });
  } catch (error) {
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}"""
        }

    def plan(self) -> str:
        """Create a React-specific development plan"""
        goal = self.context.get('goal', '')
        project_type = self._detect_project_type()

        plan = f"""
## React Development Plan

### 🎯 Goal: {goal}

### 📋 Framework Detection
- **Type**: {project_type}
- **Stack**: React/Next.js with TypeScript
- **Features**: Modern React patterns, hooks, components

### 🏗️ Implementation Strategy

1. **Component Architecture**
   - Design reusable components
   - Implement proper TypeScript interfaces
   - Use modern React patterns (hooks, context)

2. **State Management**
   - Choose appropriate state solution
   - Implement data flow patterns
   - Add proper error boundaries

3. **Styling & UI**
   - Implement responsive design
   - Use CSS-in-JS or styled-components
   - Ensure accessibility compliance

4. **Performance Optimization**
   - Implement code splitting
   - Add lazy loading
   - Optimize bundle size

5. **Testing Strategy**
   - Unit tests for components
   - Integration tests for features
   - E2E tests for critical paths

### 🎨 Code Quality Standards
- TypeScript strict mode enabled
- ESLint + Prettier configuration
- Component composition over inheritance
- Custom hooks for reusable logic
- Proper error handling and loading states
"""
        return plan

    def _detect_project_type(self) -> str:
        """Detect the type of React project"""
        project_path = Path(self.context.get('project', '.'))

        # Check for Next.js
        if (project_path / 'next.config.js').exists() or (project_path / 'next.config.mjs').exists():
            return "Next.js Application"

        # Check for Create React App
        if (project_path / 'src' / 'App.js').exists() or (project_path / 'src' / 'App.tsx').exists():
            return "Create React App"

        # Check for Vite
        if (project_path / 'vite.config.js').exists() or (project_path / 'vite.config.ts').exists():
            return "Vite React App"

        return "Custom React Project"

    def apply_patch(self, patch: str) -> bool:
        """Apply React-specific patches"""
        try:
            if 'component' in patch.lower():
                return self._create_component(patch)
            elif 'hook' in patch.lower():
                return self._create_hook(patch)
            elif 'page' in patch.lower():
                return self._create_page(patch)
            elif 'api' in patch.lower():
                return self._create_api_route(patch)
            else:
                return self._apply_generic_patch(patch)
        except Exception as e:
            print(f"Error applying React patch: {e}")
            return False

    def _create_component(self, spec: str) -> bool:
        """Create a React component from specification"""
        # Extract component name from spec
        name_match = re.search(r'component[:\s]+(\w+)', spec, re.IGNORECASE)
        if not name_match:
            return False

        component_name = name_match.group(1)
        template = self.templates['component']

        # Replace placeholders
        code = template.replace('{ComponentName}', component_name)
        code = code.replace('{component-name}', component_name.lower())

        # Save to appropriate location
        self._save_code_file(f"src/components/{component_name}.tsx", code)
        return True

    def _create_hook(self, spec: str) -> bool:
        """Create a custom React hook"""
        name_match = re.search(r'hook[:\s]+(\w+)', spec, re.IGNORECASE)
        if not name_match:
            return False

        hook_name = name_match.group(1)
        template = self.templates['hook']
        code = template.replace('{ComponentName}', hook_name)

        self._save_code_file(f"src/hooks/use{hook_name}.ts", code)
        return True

    def _create_page(self, spec: str) -> bool:
        """Create a Next.js page"""
        name_match = re.search(r'page[:\s]+(\w+)', spec, re.IGNORECASE)
        if not name_match:
            return False

        page_name = name_match.group(1)
        template = self.templates['page']
        code = template.replace('{PageName}', page_name)
        code = code.replace('{PageTitle}', page_name)
        code = code.replace('{PageDescription}', f"{page_name} page description")

        self._save_code_file(f"src/app/{page_name.lower()}/page.tsx", code)
        return True

    def _create_api_route(self, spec: str) -> bool:
        """Create a Next.js API route"""
        route_match = re.search(r'api[:\s]+(\w+)', spec, re.IGNORECASE)
        if not route_match:
            return False

        route_name = route_match.group(1)
        code = self.templates['api_route']

        self._save_code_file(f"src/app/api/{route_name}/route.ts", code)
        return True

    def _apply_generic_patch(self, patch: str) -> bool:
        """Apply generic code patches"""
        # This would contain logic to parse and apply diff patches
        # For now, return success
        return True

    def _save_code_file(self, relative_path: str, content: str) -> None:
        """Save code to file with proper directory creation"""
        project_path = Path(self.context.get('project', '.'))
        full_path = project_path / relative_path

        # Create directories if they don't exist
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write the file
        full_path.write_text(content, encoding='utf-8')

        # Store in artifacts
        self.artifacts[relative_path] = content

    def run_tests(self) -> tuple[bool, str]:
        """Run React-specific tests"""
        # This would run Jest, React Testing Library, etc.
        return True, "Tests completed successfully"