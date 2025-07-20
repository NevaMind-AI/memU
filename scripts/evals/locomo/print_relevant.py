#!/usr/bin/env python3
"""
Script to extract QA information from evaluation results file.
Extracts: CATEGORY number, Correct value, and all Relevant values from EVENT-BY-EVENT ANALYSIS.
"""

import re
import sys

def extract_qa_info(file_path):
    """
    Extract QA information from the file.
    Returns a list of tuples containing (category, correct, relevant_values_list)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        return []
    except Exception as e:
        print(f"Error reading file: {e}")
        return []
    
    results = []
    
    # Split content by QA INDEX sections
    qa_sections = re.split(r'={50,}\s*QA INDEX:', content)
    
    for i, section in enumerate(qa_sections):
        if i == 0:  # Skip the part before the first QA INDEX
            continue
            
        # Extract CATEGORY
        category_match = re.search(r'CATEGORY:\s*(\d+)', section)
        if not category_match:
            continue
        category = int(category_match.group(1))
        
        # Extract Correct value
        correct_match = re.search(r'Correct:\s*(True|False)', section)
        if not correct_match:
            continue
        correct = correct_match.group(1) == 'True'
        
        # Extract all Relevant values from EVENT-BY-EVENT ANALYSIS
        relevant_values = []
        
        # Find the EVENT-BY-EVENT ANALYSIS section
        event_analysis_match = re.search(r'EVENT-BY-EVENT ANALYSIS:(.*?)(?=ERROR ANALYSIS:|$)', section, re.DOTALL)
        if event_analysis_match:
            event_analysis_text = event_analysis_match.group(1)
            
            # Find all Relevant: True/False patterns
            relevant_matches = re.findall(r'Relevant:\s*(True|False)', event_analysis_text)
            relevant_values = [match == 'True' for match in relevant_matches]
        
        if relevant_values:  # Only add if we found relevant values
            results.append((category, correct, relevant_values))
    
    return results

def format_output(results):
    """Format the results for output"""
    output_lines = []
    
    for category, correct, relevant_values in results:
        output = f"{category:>3}   "
        output += ("+" if correct else " ") + "   "
        output += ''.join(("+" if r else "_" for r in relevant_values))
        output_lines.append(output)
    
    return output_lines

def main():
    # Extract the information
    results = extract_qa_info("./qa_error_log_20250717_205620.txt")

    # Format and display results
    for line in format_output(results):
        print(line)
    

if __name__ == "__main__":
    main() 