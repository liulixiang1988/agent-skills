# agent-skills

A collection of reusable agent skills for GitHub Copilot and AI-powered development workflows.

## Structure

- `skills/` — Individual agent skill definitions

## Usage

Browse the `skills/` directory to find skills you can use in your projects. Each skill is documented with its purpose, inputs, and expected outputs.

## Installing Skills

You can install individual skills into your project using `npx skills`:

### lumina-image

Build Docker/OCI container images, including Lumina proxy API and sandbox agent images.

```bash
npx skills add https://github.com/liulixiang1988/agent-skills --skill lumina-image
```