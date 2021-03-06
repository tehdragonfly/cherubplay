<%inherit file="base.mako" />\
<%block name="heading">Directory</%block>
    <section class="tile2">
      <h3>Welcome to the directory</h3>
      <p>The directory is a new section where you can post roleplay requests and answer other people's requests. Unlike the standard prompt and answer modes on the homepage, prompts in the directory stay up when you're not online and aren't taken down when people answer them. In addition, there's a tag system which allows you to search for or blacklist tags.</p>
      <p>Because the directory contains requests which are NSFW, triggering or otherwise unsuitable for people under 18, you'll need to pick a blacklist option before you can enter. If you are under 18 (or would otherwise like to avoid such content), we'll set you up with a default blacklist to hide anything which isn't safe for work. Alternatively if you are over 18 you can proceed without blacklisting anything.</p>
      <div class="actions">
        <form class="left" action="${request.route_path("directory_blacklist_setup")}" method="post">
          <input type="hidden" name="blacklist" value="none">
          <button type="submit">I am over 18 and want to see NSFW requests</button>
        </form>
        <form class="right" action="${request.route_path("directory_blacklist_setup")}" method="post">
          <input type="hidden" name="blacklist" value="default">
          <button type="submit">Hide NSFW requests</button>
        </form>
      </div>
    </section>
