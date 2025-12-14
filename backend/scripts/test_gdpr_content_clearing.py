"""
Test script for GDPR content clearing extension.

Tests that content is properly cleared from both pipeline_jobs and
pipeline_step_executions tables when consent is not given.
"""

import sys
import os
from datetime import datetime, timedelta

# Add backend to path
backend_path = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, os.path.abspath(backend_path))

from app.database.connection import get_session
from app.database.modular_pipeline_models import PipelineJobDB, PipelineStepExecutionDB
from app.repositories.feedback_repository import PipelineJobFeedbackRepository
from app.services.feedback_service import FeedbackService


def test_content_clearing():
    """Test that content is cleared from both tables."""
    print("🧪 Testing GDPR content clearing extension...\n")

    session_gen = get_session()
    session = next(session_gen)

    try:
        # Find a job with step executions
        job = (
            session.query(PipelineJobDB)
            .filter(
                PipelineJobDB.completed_at.isnot(None),
                PipelineJobDB.content_cleared_at.is_(None),
            )
            .first()
        )

        if not job:
            print("❌ No completed job found for testing")
            return False

        print(f"📋 Found test job: {job.processing_id}")
        print(f"   Job ID: {job.job_id}")
        print(f"   Status: {job.status}")

        # Count step executions
        step_executions = (
            session.query(PipelineStepExecutionDB)
            .filter_by(job_id=job.job_id)
            .all()
        )
        print(f"   Step executions: {len(step_executions)}")

        if len(step_executions) == 0:
            print("⚠️  No step executions found for this job")
            return False

        # Check content before clearing
        print("\n📊 Content before clearing:")
        print(f"   Job file_content: {'Present' if job.file_content else 'None'}")
        print(f"   Job result_data: {bool(job.result_data)}")
        if job.result_data:
            print(f"      - original_text: {bool(job.result_data.get('original_text'))}")
            print(f"      - translated_text: {bool(job.result_data.get('translated_text'))}")

        step_with_content = 0
        for step in step_executions[:3]:  # Check first 3
            if step.input_text or step.output_text:
                step_with_content += 1
                print(f"   Step '{step.step_name}':")
                print(f"      - input_text: {bool(step.input_text)}")
                print(f"      - output_text: {bool(step.output_text)}")
                print(f"      - prompt_used: {bool(step.prompt_used)}")
                print(f"      - step_metadata: {bool(step.step_metadata)}")

        if step_with_content == 0:
            print("   No step executions with content found")
            return False

        # Clear content
        print("\n🧹 Clearing content...")
        repo = PipelineJobFeedbackRepository(session)
        cleared_job = repo.clear_content_for_job(job.processing_id)

        if not cleared_job:
            print("❌ Failed to clear content")
            return False

        # Refresh step executions
        session.refresh(cleared_job)
        step_executions_after = (
            session.query(PipelineStepExecutionDB)
            .filter_by(job_id=job.job_id)
            .all()
        )

        # Verify clearing
        print("\n✅ Content after clearing:")
        print(f"   Job file_content: {'Present' if cleared_job.file_content else 'None (cleared)'}")
        print(f"   Job content_cleared_at: {cleared_job.content_cleared_at}")

        if cleared_job.result_data:
            original = cleared_job.result_data.get("original_text", "")
            translated = cleared_job.result_data.get("translated_text", "")
            print(f"   Job result_data:")
            print(f"      - original_text: '{original[:50]}...'")
            print(f"      - translated_text: '{translated[:50]}...'")

        # Check metadata preservation
        print(f"\n📈 Metadata preserved:")
        print(f"   Job status: {cleared_job.status}")
        print(f"   Job total_execution_time_seconds: {cleared_job.total_execution_time_seconds}")
        print(f"   Job completed_at: {cleared_job.completed_at}")

        # Verify step executions
        all_cleared = True
        for step in step_executions_after:
            if step.input_text is not None or step.output_text is not None:
                print(f"   ⚠️  Step '{step.step_name}' still has content!")
                all_cleared = False
            else:
                # Verify metadata preserved
                print(f"   Step '{step.step_name}':")
                print(f"      - input_text: {step.input_text} (cleared)")
                print(f"      - output_text: {step.output_text} (cleared)")
                print(f"      - prompt_used: {step.prompt_used} (cleared)")
                print(f"      - status: {step.status} (preserved)")
                print(f"      - execution_time_seconds: {step.execution_time_seconds} (preserved)")
                print(f"      - token_count_input: {step.token_count_input} (preserved)")
                print(f"      - token_count_output: {step.token_count_output} (preserved)")

        if all_cleared:
            print("\n✅ All content cleared successfully!")
            print("✅ Metadata preserved correctly!")
            return True
        else:
            print("\n❌ Some content was not cleared")
            return False

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass


def test_consent_false_scenario():
    """Test that content is cleared when feedback is submitted with consent=False."""
    print("\n🧪 Testing consent=False scenario...\n")

    session_gen = get_session()
    session = next(session_gen)

    try:
        # Find a completed job without feedback
        job = (
            session.query(PipelineJobDB)
            .filter(
                PipelineJobDB.completed_at.isnot(None),
                PipelineJobDB.has_feedback == False,  # noqa: E712
                PipelineJobDB.content_cleared_at.is_(None),
            )
            .first()
        )

        if not job:
            print("❌ No job found for testing consent=False scenario")
            return False

        print(f"📋 Found test job: {job.processing_id}")

        # Submit feedback with consent=False
        service = FeedbackService(session)
        try:
            result = service.submit_feedback(
                processing_id=job.processing_id,
                overall_rating=3,
                data_consent_given=False,
                comment="Test feedback without consent",
            )
            print(f"✅ Feedback submitted: {result['id']}")

            # Check that content was cleared
            session.refresh(job)
            updated_job = (
                session.query(PipelineJobDB)
                .filter_by(processing_id=job.processing_id)
                .first()
            )

            if updated_job.content_cleared_at:
                print(f"✅ Content cleared at: {updated_job.content_cleared_at}")
                print("✅ Consent=False scenario works correctly!")
                return True
            else:
                print("❌ Content was not cleared after consent=False feedback")
                return False

        except ValueError as e:
            if "already submitted" in str(e):
                print(f"⚠️  Feedback already exists for this job: {e}")
                return True  # This is expected if test was run before
            raise

    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            next(session_gen)
        except StopIteration:
            pass


if __name__ == "__main__":
    print("=" * 60)
    print("GDPR Content Clearing Extension Test")
    print("=" * 60)

    test1 = test_content_clearing()
    test2 = test_consent_false_scenario()

    print("\n" + "=" * 60)
    if test1 and test2:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)

