// A política de segurança do site não permite scripts inline; tudo fica aqui.

// 1) Confirmação antes de enviar formulários marcados com data-confirmar.
document.addEventListener("submit", function (evento) {
  var mensagem = evento.target.getAttribute("data-confirmar");
  if (mensagem && !window.confirm(mensagem)) {
    evento.preventDefault();
  }
});

// 2) Menu: sempre aberto em telas largas; recolhido (botão "Menu") em telas estreitas.
(function () {
  var menu = document.querySelector("details.menu-toggle");
  if (!menu || !window.matchMedia) { return; }
  var larga = window.matchMedia("(min-width: 861px)");
  function ajustar() { menu.open = larga.matches; }
  ajustar();
  if (larga.addEventListener) { larga.addEventListener("change", ajustar); }
})();
