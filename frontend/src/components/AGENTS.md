# FRONTEND COMPONENTS

UI component library using shadcn/ui and Tailwind CSS v4.

## STRUCTURE

- **ui/**: 25 shadcn/ui primitive components (Button, Card, Dialog, Table, etc.).
- **evaluation/**: Domain-specific components for assessment forms and results.
- **app-layout.tsx**: Main application shell including sidebar and header.
- **auth-guard.tsx**: Route protection for authenticated sessions.
- **pingcastle-terminal.tsx**: Custom terminal emulator for PingCastle output.
- **skeletons.tsx**: React Suspense loading states.
- **theme-toggle.tsx**: Dark/light mode switcher.

## CONVENTIONS

### shadcn/ui Primitives
These live in `ui/`. Do not modify these files manually as the shadcn CLI manages them.
To add a new primitive:
`npx shadcn@latest add [component]`

### Custom Components
Create new components in the root of `components/` or a relevant subdirectory.
- Use functional components with TypeScript interfaces for props.
- Use the `cn()` helper from `@/lib/utils` for conditional class merging.
- Prefer Tailwind utility classes over custom CSS.

### Imports
- Primitives: `import { Button } from "@/components/ui/button"`
- Custom: `import { AppLayout } from "@/components/app-layout"`

## STYLING
Tailwind CSS v4 with CSS-based configuration. Always check for dark mode compatibility using the `dark:` variant.
