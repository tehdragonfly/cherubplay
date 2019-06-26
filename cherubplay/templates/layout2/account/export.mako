<%inherit file="base.mako" />\
<%block name="heading">Export your acccount data</%block>
  % if can_export:
    <% pass %>
  % else:
    <section class="tile2">
      <p>This page will allow you to export all of your account data, including your chats, your prompts and your directory requests.</p>
      <p>The export function is not available to you yet. You'll be able to use it on ${request.user.localise_time(rollout_time).strftime("%A %d %B at %H:%M")}.</p>
    </section>
    <form action="" method="post"><button type="submit">Export</button></form>
  % endif
