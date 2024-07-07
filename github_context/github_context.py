#!/usr/bin/env python3

import os
import sys
import argparse
import pyperclip
from github import Github
import base64
from typing import Optional, List
from github.Repository import Repository
from github.ContentFile import ContentFile

def add_content(header: str, content: str) -> str:
    return f"{'='*50}\n{header}\n{'='*50}\n\n{content}\n\n"

def should_ignore(path: str, ignore_patterns: List[str]) -> bool:
    return any(pattern in path for pattern in ignore_patterns) or path == '.gitignore'

def extract_repo_content(repo: Repository, path: str = '', ignore_patterns: List[str] = []) -> str:
    all_content = ""
    contents: List[ContentFile] = repo.get_contents(path)
    for content_file in contents:
        if content_file.type == "dir":
            all_content += extract_repo_content(repo, content_file.path, ignore_patterns)
        elif not should_ignore(content_file.path, ignore_patterns):
            try:
                file_content = base64.b64decode(content_file.content).decode('utf-8')
                all_content += add_content(f"File: {content_file.path}", file_content)
            except Exception as e:
                print(f"Error extracting {content_file.path}: {str(e)}")
    return all_content

def extract_issues(repo: Repository) -> str:
    all_content = ""
    issues = repo.get_issues(state='all')
    for issue in issues:
        content = f"Issue #{issue.number}: {issue.title}\n\n{issue.body}\n\nComments:\n"
        for comment in issue.get_comments():
            content += f"- {comment.user.login}: {comment.body}\n\n"
        all_content += add_content(f"Issue: #{issue.number}", content)
    return all_content

def extract_wiki(repo: Repository) -> str:
    all_content = ""
    try:
        wiki = repo.get_wiki()
        for page in wiki.get_pages():
            content = page.content
            all_content += add_content(f"Wiki Page: {page.title}", content)
    except AttributeError:
        # Silently ignore if there's no wiki
        pass
    except Exception as e:
        print(f"Error extracting wiki: {str(e)}")
    return all_content

def main() -> None:
    parser = argparse.ArgumentParser(description="Extract content from a GitHub repository.")
    parser.add_argument("repo", help="Repository name in the format 'owner/repo'")
    parser.add_argument("--issues-only", action="store_true", help="Extract only issues")
    parser.add_argument("--wiki-only", action="store_true", help="Extract only wiki")
    parser.add_argument("--no-issues", action="store_true", help="Do not extract issues")
    parser.add_argument("--no-wiki", action="store_true", help="Do not extract wiki")
    parser.add_argument("--output", help="Output directory for the text file")
    args = parser.parse_args()

    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        print("Please set the GITHUB_TOKEN environment variable")
        sys.exit(1)

    g = Github(github_token)
    repo = g.get_repo(args.repo)

    all_content = f"Content of {args.repo}\n\n"

    try:
        ignore_patterns: List[str] = []
        try:
            gitignore_content = repo.get_contents(".gitignore").decoded_content.decode('utf-8')
            ignore_patterns = [line.strip() for line in gitignore_content.split('\n') if line.strip() and not line.startswith('#')]
        except Exception:
            pass  # Silently ignore if there's no .gitignore file

        if not args.issues_only and not args.wiki_only:
            all_content += extract_repo_content(repo, ignore_patterns=ignore_patterns)
        
        if not args.no_issues and not args.wiki_only:
            all_content += extract_issues(repo)
        
        if not args.no_wiki and not args.issues_only:
            all_content += extract_wiki(repo)

        if args.output:
            output_filename = os.path.join(args.output, f"{args.repo.replace('/', '_')}_content.txt")
            with open(output_filename, 'w', encoding='utf-8') as f:
                f.write(all_content)
            print(f"Repository content extracted to '{output_filename}'")
        else:
            pyperclip.copy(all_content)
            print("Repository content copied to clipboard")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
