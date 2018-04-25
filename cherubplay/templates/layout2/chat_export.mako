<%inherit file="chat_base.mako" />\
    % if export and export.filename:
      <section class="tile2">
        <h3>Export complete</h3>
        <p>This chat was exported on ${request.user.localise_time(export.generated).strftime("%Y-%m-%d at %H:%M:%S")}.</p>
        <p>Please download it soon - it will expire on ${request.user.localise_time(export.generated).strftime("%Y-%m-%d at %H:%M:%S")}.</p>
        <div class="middle_actions">
          <a href="${request.registry.settings["export_url"]}/${request.context.chat.url}/${export.celery_task_id}/${export.filename}">Download</a>
        </div>
      </section>
    % elif export:
      <section class="tile2">
        <h2>Export in progress</h2>
        <p>Please wait while we export this chat. It could take a few minutes.</p>
      </section>
    % else:
      <form class="tile2" action="${request.route_path("chat_export", url=request.context.chat.url)}" method="POST">
        <h3>Export this chat</h3>
        <p>TODO</p>
        <div class="middle_actions">
          <button type="submit">Begin export</button>
        </div>
      </form>
    % endif
