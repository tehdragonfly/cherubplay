<%inherit file="base.mako" />\
<%block name="heading">Directory</%block>
    <section class="tile2">
      <h3>Welcome to the directory</h3>
      <p>The directory is a new section where you can post roleplay requests and answer other people's reqests. Unlike the standard prompt and anwer modes on the homepage, prompts in the directory stay up when you're not online and can be answered by more than one person. In addition, there's a tag system which allows you to search for or blacklist tags.</p>
      <p>Because the directory contains requests which are NSFW, triggering or otherwise objectionable, you'll need to pick a blacklist option before you can enter. If you'd like to avoid such content, we can set you up with a default blacklist including the NSFW and NSFW extreme categories and many common triggers. Alternatively you can proceed without blacklisting anything.</p>
      <div class="actions">
        <form class="left" action="${request.route_path("directory_blacklist_setup")}" method="post">
          <input type="hidden" name="blacklist" value="none">
          <button type="submit">No blacklist</button>
        </form>
        <form class="right" action="${request.route_path("directory_blacklist_setup")}" method="post">
          <input type="hidden" name="blacklist" value="default">
          <button type="submit">Default blacklist</button>
        </form>
      </div>
    </section>
