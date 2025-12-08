"""
CLI Entry Point for Smart Data Pipeline

Usage:
    python -m src add <url>        Add a new data source
    python -m src status           Show health status
    python -m src fix <source>     Force repair of a source
    python -m src run              Run orchestrator loop
    python -m src run --once       Process one task and exit
"""
import argparse
import sys
from datetime import datetime

from dotenv import load_dotenv
from src.utils.logger import logger

# Load environment variables
load_dotenv()


def cmd_add(args):
    """Add a new data source."""
    from src.orchestration.orchestrator import Orchestrator
    
    orch = Orchestrator()
    task = orch.add_source(args.url, priority=args.priority)
    
    logger.info(f"Task queued: [{task.task_id}] ADD_SOURCE → {args.url}")
    
    if args.now:
        logger.info("Processing immediately...")
        orch.startup()
        orch.process_task(task)


def cmd_status(args):
    """Show current status."""
    from src.orchestration.orchestrator import Orchestrator
    
    orch = Orchestrator()
    status = orch.status()
    
    logger.info("Pipeline Status")
    logger.info("=" * 50)
    logger.info(f"Pending Tasks: {status['pending_tasks']}")
    logger.info(f"Total Sources: {status['total_sources']}")
    
    # Status breakdown
    logger.info("Health Summary:")
    logger.info(f"  ✅ Active:      {status['healthy']}")
    logger.info(f"  ⚠️  Degraded:    {status['degraded']}")
    logger.info(f"  🔒 Quarantined: {status['quarantined']}")
    logger.info(f"  💀 Dead:        {status['dead']}")
    
    # Source details
    if status['sources']:
        logger.info("Sources:")
        logger.info("-" * 50)
        for s in status['sources']:
            icon = {
                'ACTIVE': '✅',
                'DEGRADED': '⚠️',
                'QUARANTINED': '🔒',
                'DEAD': '💀',
            }.get(s['state'], '❓')
            
            last_success = s['last_success'] or 'never'
            if isinstance(last_success, str) and last_success != 'never':
                # Format nicely
                try:
                    dt = datetime.fromisoformat(last_success)
                    last_success = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            logger.info(f"  {icon} {s['name']:<30} (failures: {s['failures']}, last: {last_success})")
    else:
        logger.info("No sources registered yet.")


def cmd_fix(args):
    """Force repair of a source."""
    from src.orchestration.orchestrator import Orchestrator
    
    orch = Orchestrator()
    task = orch.fix_source(args.source, priority=10)
    
    logger.info(f"Repair queued: [{task.task_id}] FIX_SOURCE → {args.source}")
    
    if args.now:
        logger.info("Processing immediately...")
        orch.startup()
        orch.process_task(task)


def cmd_run(args):
    """Run the orchestrator loop."""
    from src.orchestration.orchestrator import Orchestrator
    
    orch = Orchestrator()
    
    logger.info("Starting orchestrator...")
    logger.info("Press Ctrl+C to stop")
    
    try:
        orch.run(once=args.once)
    except KeyboardInterrupt:
        logger.info("Stopping...")
        orch.stop()


def cmd_tasks(args):
    """Show task queue."""
    from src.orchestration.task_queue import TaskQueue
    
    tq = TaskQueue()
    tasks = tq.get_all_tasks(limit=args.limit)
    
    logger.info("Task Queue")
    logger.info("=" * 70)
    
    if not tasks:
        logger.info("No tasks in queue.")
    else:
        logger.info(f"{'ID':<5} {'Type':<15} {'State':<12} {'Target':<30}")
        logger.info("-" * 70)
        for t in tasks:
            logger.info(f"{t.task_id:<5} {t.task_type.value:<15} {t.state.value:<12} {t.target[:30]:<30}")


def main():
    parser = argparse.ArgumentParser(
        prog="python -m src",
        description="Smart Data Pipeline CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new data source")
    add_parser.add_argument("url", help="URL to analyze and scrape")
    add_parser.add_argument("--priority", type=int, default=5, help="Task priority (1-10)")
    add_parser.add_argument("--now", action="store_true", help="Process immediately")
    add_parser.set_defaults(func=cmd_add)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show health status")
    status_parser.set_defaults(func=cmd_status)
    
    # Fix command
    fix_parser = subparsers.add_parser("fix", help="Force repair of a source")
    fix_parser.add_argument("source", help="Source name to repair")
    fix_parser.add_argument("--now", action="store_true", help="Process immediately")
    fix_parser.set_defaults(func=cmd_fix)
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run orchestrator loop")
    run_parser.add_argument("--once", action="store_true", help="Process one task and exit")
    run_parser.set_defaults(func=cmd_run)
    
    # Tasks command
    tasks_parser = subparsers.add_parser("tasks", help="Show task queue")
    tasks_parser.add_argument("--limit", type=int, default=20, help="Max tasks to show")
    tasks_parser.set_defaults(func=cmd_tasks)
    
    # Parse and execute
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    
    args.func(args)


if __name__ == "__main__":
    main()
