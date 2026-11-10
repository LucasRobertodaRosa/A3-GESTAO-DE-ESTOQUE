// Confirmação antes de enviar formulários marcados com data-confirmar
// (a política de segurança do site não permite scripts inline).
document.addEventListener("submit", function (evento) {
  var mensagem = evento.target.getAttribute("data-confirmar");
  if (mensagem && !window.confirm(mensagem)) {
    evento.preventDefault();
  }
});
