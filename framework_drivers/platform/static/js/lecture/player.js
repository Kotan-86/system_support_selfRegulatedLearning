// 仕様: docs/spec/framework-drivers-layer.md#技術選定確定
// 仕様: docs/spec/framework-drivers-implementation-plan.md#Phase-5-講義動画フロント
(function (global) {
  "use strict";

  var participantId = global.ParticipantContext.getParticipantIdFromUrl();
  if (!participantId) {
    return;
  }

  var videoId = global.__LECTURE_VIDEO_ID__;
  var player = null;
  var timer = null;
  var currentTime = 0;
  var isSkipping = false;
  var isSeeking = false;
  var isDragging = false;
  var range = null;
  var prevTime = 0;

  function recordLog(currentTimeValue, action, duration) {
    global.ApiClient.postViewingLog(
      participantId,
      currentTimeValue,
      action,
      duration
    );
  }

  function getWindowSize() {
    return {
      width:
        global.innerWidth ||
        document.documentElement.clientWidth ||
        document.body.clientWidth,
      height:
        global.innerHeight ||
        document.documentElement.clientHeight ||
        document.body.clientHeight,
    };
  }

  function setPlayerSize(ytPlayer) {
    var windowSize = getWindowSize();
    var playerWidth = windowSize.width * 0.5;
    var playerHeight = (playerWidth * 9) / 16;
    ytPlayer.setSize(playerWidth, playerHeight);
    seekBar();
  }

  function formattime(seconds) {
    var strTime = Math.floor(Number(seconds) / 3600) + ":";
    strTime +=
      ("00" + Math.floor(Number(seconds) / 60)).slice(-2) + ":";
    strTime += ("00" + Math.floor(Number(seconds) % 60)).slice(-2);
    return strTime;
  }

  function seekbarJumpto(value) {
    range.value = value;
    document.getElementById("time").innerHTML = formattime(range.value);
  }

  function syncSeekBar() {
    if (player && typeof player.getCurrentTime === "function") {
      seekbarJumpto(player.getCurrentTime());
    }
  }

  function seekBar() {
    range = document.getElementById("seekbar");
    var playerElement = document.getElementById("player");
    if (!range || !playerElement) {
      return;
    }
    range.style.width = playerElement.offsetWidth + "px";

    range.addEventListener("change", function () {
      isDragging = false;
      document.getElementById("time").innerHTML = formattime(range.value);
      sessionStorage.removeItem("currenttime");
      if (prevTime < range.value) {
        forwardSeek(range.value - prevTime, prevTime, range.value);
      } else if (prevTime > range.value) {
        backwardSeek(range.value - prevTime, prevTime, range.value);
      }
    });

    range.addEventListener("input", function () {
      if (sessionStorage.getItem("currenttime") === null) {
        isDragging = true;
        prevTime = player.getCurrentTime();
        sessionStorage.setItem("currenttime", range.value);
        player.pauseVideo();
        if (timer) {
          clearInterval(timer);
        }
      }
    });
  }

  function onPlayerReady(event) {
    range = document.getElementById("seekbar");
    range.max = player.getDuration();
    event.target.playVideo();
    setPlayerSize(player);
    player.pauseVideo();
  }

  function onPlayerStateChange(event) {
    var position = player.getCurrentTime();
    if (event.data === YT.PlayerState.PLAYING) {
      if (timer) {
        clearInterval(timer);
      }
      timer = setInterval(syncSeekBar, 500);
      if (player.getDuration()) {
        range.max = player.getDuration();
      }
      if (isSkipping) {
        isSkipping = false;
      } else if (isSeeking) {
        isSeeking = false;
      } else {
        recordLog(position, "play", 0);
      }
    } else if (event.data === YT.PlayerState.PAUSED) {
      if (timer) {
        clearInterval(timer);
      }
      if (isDragging) {
        return;
      }
      recordLog(position, "pause", 0);
    } else if (timer) {
      clearInterval(timer);
    }
  }

  global.onYouTubeIframeAPIReady = function () {
    player = new YT.Player("player", {
      height: (1200 * 9) / 16,
      width: 1200,
      videoId: videoId,
      playerVars: {
        cc_load_policy: 1,
        controls: 0,
        disablekb: 1,
        iv_load_policy: 3,
        modestbranding: 1,
        rel: 0,
        enablejsapi: 1,
      },
      events: {
        onReady: onPlayerReady,
        onStateChange: onPlayerStateChange,
      },
    });
  };

  global.addEventListener("resize", function () {
    if (player && typeof player.setSize === "function") {
      setPlayerSize(player);
      seekBar();
    }
  });

  global.play = function () {
    player.playVideo();
  };

  global.pause = function () {
    player.pauseVideo();
  };

  global.forwardSkip = function () {
    isSkipping = true;
    var toSkipTime = 5;
    var currentBarValue = Number(document.getElementById("seekbar").value);
    var destTime = currentBarValue + toSkipTime;
    var duration = player.getDuration();
    if (destTime > duration) {
      destTime = duration;
    }
    player.seekTo(destTime, true);
    seekbarJumpto(destTime);
    currentTime = destTime;
    recordLog(currentTime, "forward_skip", 5);
  };

  global.backwardSkip = function () {
    isSkipping = true;
    var toSkipTime = -5;
    var currentBarValue = Number(document.getElementById("seekbar").value);
    var destTime = currentBarValue + toSkipTime;
    if (destTime < 0) {
      destTime = 0;
    }
    player.seekTo(destTime, true);
    seekbarJumpto(destTime);
    currentTime = destTime;
    recordLog(currentTime, "backward_skip", -5);
  };

  function forwardSeek(duration, fromTime, toSeekTime) {
    isSeeking = true;
    player.seekTo(toSeekTime, true);
    seekbarJumpto(toSeekTime);
    player.playVideo();
    currentTime = fromTime + duration;
    recordLog(currentTime, "forward_seek", duration);
  }

  function backwardSeek(duration, fromTime, toSeekTime) {
    isSeeking = true;
    player.seekTo(toSeekTime, true);
    seekbarJumpto(toSeekTime);
    player.playVideo();
    currentTime = fromTime + duration;
    recordLog(currentTime, "backward_seek", duration);
  }
})(window);
