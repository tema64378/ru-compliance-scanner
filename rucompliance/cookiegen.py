"""Генератор RU-compliant cookie-баннера.

Готовый сниппет: «Принять / Отклонить», выбор сохраняется в localStorage,
аналитика грузится ТОЛЬКО после согласия (требование РКН с 01.09.2025).
"""


def cookie_banner(policy_url="/privacy", accent="#0077FF"):
    return """<!-- 152чек: cookie-баннер. Вставьте перед </body>. Счётчики кладите в loadAnalytics(). -->
<div id="cc-banner" style="display:none;position:fixed;left:16px;right:16px;bottom:16px;z-index:9999;
  max-width:760px;margin:0 auto;background:#fff;border:1px solid #e3e6eb;border-radius:14px;
  box-shadow:0 10px 30px rgba(0,0,0,.14);padding:16px 18px;font-family:system-ui,Arial,sans-serif">
  <div style="font-size:14px;color:#16181b;line-height:1.5">
    Мы используем файлы cookie для работы сайта и аналитики. Подробнее — в
    <a href="__POLICY__" style="color:__ACCENT__">политике обработки данных</a>.
  </div>
  <div style="margin-top:12px;display:flex;gap:10px;flex-wrap:wrap">
    <button onclick="ccConsent(true)" style="background:__ACCENT__;color:#fff;border:0;border-radius:10px;
      padding:9px 18px;font-weight:600;cursor:pointer">Принять</button>
    <button onclick="ccConsent(false)" style="background:#fff;color:#16181b;border:1.5px solid #e3e6eb;
      border-radius:10px;padding:9px 18px;cursor:pointer">Отклонить</button>
  </div>
</div>
<script>
  function loadAnalytics(){
    /* ⬇️ ВСТАВЬ СЮДА свои счётчики (Яндекс.Метрика / Google Analytics).
       Они грузятся ТОЛЬКО после согласия пользователя. */
  }
  function ccConsent(yes){
    try{ localStorage.setItem("cc-consent", yes ? "yes" : "no"); }catch(e){}
    var b=document.getElementById("cc-banner"); if(b) b.style.display="none";
    if(yes) loadAnalytics();
  }
  (function(){
    var c=null; try{ c=localStorage.getItem("cc-consent"); }catch(e){}
    if(c==="yes"){ loadAnalytics(); }
    else if(c!=="no"){ var b=document.getElementById("cc-banner"); if(b) b.style.display="block"; }
  })();
</script>""".replace("__POLICY__", policy_url).replace("__ACCENT__", accent)
