import json
import six
from memorious.logic.context import Context


class TestContext(object):
    def test_context(self, context):
        assert isinstance(context.run_id, six.string_types)

    def test_content_hash(self, context):
        content_hash = context.store_data(json.dumps({"hello": "world"}))
        assert isinstance(content_hash, six.string_types)
        with context.load_file(content_hash) as fh:
            assert isinstance(fh, file)

    def test_dump_load_state(self, context, crawler, stage):
        dump = context.dump_state()
        new_context = Context.from_state(dump, stage.name)
        assert isinstance(new_context, Context)
        assert new_context.run_id == context.run_id
        assert new_context.crawler.name == crawler.name
        assert new_context.stage.name == stage.name
        assert all(
            (k, v) in new_context.state.items()
            for k, v in context.state.items()
        )
