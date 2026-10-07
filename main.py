# main.py
import sys
import os
import uuid
from datetime import datetime
from database.registry import register_csv, register_parquet, list_registered_tables
from database.connection import close_duckdb_connection
from agents.orchestrator import run_orchestrator_pipeline

def new_session_id() -> str:
    """
    Generates a unique session ID with the current timestamp and a short UUID suffix.
    """
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"session-{timestamp}-{uuid.uuid4().hex[:6]}"

def print_help():
    print("\n--- Available Commands ---")
    print("  /load <file_path>  - Register a CSV or Parquet file as a database table")
    print("  /tables            - List all registered tables and views")
    print("  /session           - Print the current Session ID and User ID")
    print("  /new               - Start a new conversation (generates a new Session ID)")
    print("  /help              - Show this help message")
    print("  /quit or /exit     - Close the program")
    print("--------------------------\n")

def main():
    print("==================================================")
    print("   Welcome to the Text-to-SQL Agentic AI (CLI)    ")
    print("==================================================")
    
    # 1. Prompt the user for their Client/User ID
    user_id = input("Enter User/Client ID (default: guest_user): ").strip()
    if not user_id:
        user_id = "guest_user"
        
    # 2. Generate initial session ID
    session_id = new_session_id()
    
    print(f"\nInitialized Active Session:")
    print(f"  👤 User ID:    {user_id}")
    print(f"  🔑 Session ID: {session_id}")
    print("\nType your natural language questions below.")
    print("Or type /help to see command options.")
    print("==================================================")
    
    while True:
        try:
            # Command Prompt
            user_input = input(f"\n[{user_id}] >>> ").strip()
            
            if not user_input:
                continue
                
            # Handle Slash Commands
            if user_input.startswith("/"):
                parts = user_input.split(maxsplit=1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""
                
                if cmd in ["/quit", "/exit"]:
                    print("\nExiting Text-to-SQL system. Goodbye!")
                    break
                    
                elif cmd == "/help":
                    print_help()
                    
                elif cmd == "/session":
                    print(f"\nCurrent Active Session Details:")
                    print(f"  👤 User ID:    {user_id}")
                    print(f"  🔑 Session ID: {session_id}")
                    
                elif cmd == "/new":
                    session_id = new_session_id()
                    print(f"\nStarted a new conversation session!")
                    print(f"  🔑 New Session ID: {session_id}")
                    
                elif cmd == "/tables":
                    tables = list_registered_tables()
                    if tables:
                        print("\nRegistered Database Tables/Views:")
                        for idx, table in enumerate(tables, 1):
                            print(f"  {idx}. {table}")
                    else:
                        print("\nNo tables or views registered yet. Use '/load <file>' to load data.")
                        
                elif cmd == "/load":
                    if not arg:
                        print("Error: Please provide a file path. Example: /load data/sales.csv")
                        continue
                        
                    file_path = arg.strip()
                    # Strip outer quotes if paths are drag-and-dropped
                    if file_path.startswith(('"', "'")) and file_path.endswith(('"', "'")):
                        file_path = file_path[1:-1]
                        
                    if not os.path.exists(file_path):
                        print(f"Error: File not found at '{file_path}'")
                        continue
                        
                    # Infer sanitized table name from base file name
                    base_name = os.path.basename(file_path)
                    name_without_ext, ext = os.path.splitext(base_name)
                    table_name = name_without_ext.lower().replace("-", "_").replace(" ", "_")
                    
                    try:
                        ext_lower = ext.lower()
                        if ext_lower == ".csv":
                            register_csv(file_path, table_name)
                            print(f"Success: Registered CSV file as table '{table_name}'")
                        elif ext_lower == ".parquet":
                            register_parquet(file_path, table_name)
                            print(f"Success: Registered Parquet file as table '{table_name}'")
                        else:
                            print(f"Error: Unsupported file format '{ext}'. Only .csv and .parquet are supported.")
                    except Exception as e:
                        print(f"Error loading file: {e}")
                        
                else:
                    print(f"Unknown command '{cmd}'. Type /help to see all commands.")
                    
            else:
                # Process natural language question using Orchestrator Pipeline
                print("\nProcessing request, please wait...")
                response = run_orchestrator_pipeline(
                    question=user_input,
                    session_id=session_id,
                    user_id=user_id
                )
                print("\n--- Response ---")
                print(response)
                print("----------------")
                
        except KeyboardInterrupt:
            print("\nUse /quit to exit the system.")
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            
    # Clean up connection when closing REPL
    close_duckdb_connection()

if __name__ == "__main__":
    main()
