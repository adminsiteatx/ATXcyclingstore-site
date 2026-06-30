import os

from django.contrib.auth.models import User
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from twilio.rest import Client as TwilioClient

from .models import Cliente, Booking
from .views import _entrega, MESES_PT
from .signals import _resend_send

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://atxcyclingstore.vercel.app")


# ---------------------------------------------------------------------------
# Registo
# ---------------------------------------------------------------------------

class RegisterView(APIView):
    def post(self, request):
        nome     = request.data.get('nome', '').strip()
        email    = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        telefone = request.data.get('telefone', '').strip()
        aceita_sms = request.data.get('aceita_sms', True)

        if not all([nome, email, password, telefone]):
            return Response({'error': 'Todos os campos são obrigatórios.'}, status=400)

        if User.objects.filter(email=email).exists():
            return Response({'error': 'Já existe uma conta com este email.'}, status=400)

        first, *rest = nome.split(' ', 1)
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first,
            last_name=rest[0] if rest else '',
        )
        Cliente.objects.create(user=user, telefone=telefone, aceita_sms=aceita_sms)

        # ligar marcações antigas pelo email
        Booking.objects.filter(email=email, user__isnull=True).update(user=user)

        tokens = RefreshToken.for_user(user)
        return Response({
            'access':  str(tokens.access_token),
            'refresh': str(tokens),
            'nome':    user.get_full_name(),
            'email':   user.email,
        }, status=201)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginView(APIView):
    def post(self, request):
        from django.contrib.auth import authenticate
        email    = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')

        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({'error': 'Email ou password incorretos.'}, status=401)

        tokens = RefreshToken.for_user(user)
        return Response({
            'access':  str(tokens.access_token),
            'refresh': str(tokens),
            'nome':    user.get_full_name(),
            'email':   user.email,
        })


# ---------------------------------------------------------------------------
# Dados do utilizador autenticado
# ---------------------------------------------------------------------------

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        try:
            tel = user.cliente.telefone
            aceita_sms = user.cliente.aceita_sms
        except Cliente.DoesNotExist:
            tel = ''
            aceita_sms = False
        return Response({
            'nome':       user.get_full_name(),
            'email':      user.email,
            'telefone':   tel,
            'aceita_sms': aceita_sms,
        })


# ---------------------------------------------------------------------------
# Histórico de marcações do utilizador
# ---------------------------------------------------------------------------

class MinhasMarcacoesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        bookings = Booking.objects.filter(
            user=user
        ).order_by('-criado_em')

        data = [{
            'id':              b.id,
            'numero_pedido':   b.numero_pedido,
            'data':            b.data.isoformat(),
            'entrega_prevista': _entrega(b.data),
            'estado':          b.estado,
            'estado_label':    b.get_estado_display(),
            'servico':         _parse_servico(b.mensagem),
            'mensagem':        _parse_mensagem(b.mensagem),
            'token_tracking':  str(b.token_tracking),
            'pode_cancelar':   b.estado in ('marcada', 'recebida', 'diagnostico'),
        } for b in bookings]
        return Response(data)


def _parse_mensagem(mensagem):
    """Devolve só o texto livre, sem o prefixo '[Serviço — Bicicleta]'."""
    if mensagem and mensagem.startswith('['):
        try:
            return mensagem[mensagem.index(']') + 1:].strip()
        except ValueError:
            pass
    return mensagem or ''


# ---------------------------------------------------------------------------
# Cancelar marcação (cliente, com restrição de estado)
# ---------------------------------------------------------------------------

class MinhaCancelarMarcacaoView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, booking_id):
        try:
            booking = Booking.objects.get(id=booking_id, user=request.user)
        except Booking.DoesNotExist:
            return Response({'error': 'Marcação não encontrada.'}, status=404)

        if booking.estado not in ('marcada', 'recebida', 'diagnostico'):
            return Response(
                {'error': 'Esta marcação já está em reparação ou concluída e não pode ser cancelada online. Contacta a loja.'},
                status=400,
            )

        booking.delete()
        return Response({'message': 'Marcação cancelada com sucesso.'})


def _parse_servico(mensagem):
    """Extrai o serviço da mensagem no formato '[Serviço — Bicicleta] texto'"""
    if mensagem and mensagem.startswith('['):
        try:
            return mensagem[1:mensagem.index(']')]
        except ValueError:
            pass
    return ''


# ---------------------------------------------------------------------------
# SMS em massa (gestor)
# ---------------------------------------------------------------------------

from .views import GESTAO_TOKEN


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        user = request.user
        user.delete()
        return Response({'message': 'Conta eliminada com sucesso.'})


class SmsBroadcastView(APIView):
    def post(self, request):
        token = request.headers.get('X-Gestao-Token', '')
        if token != GESTAO_TOKEN:
            return Response({'error': 'Não autorizado'}, status=401)

        mensagem = request.data.get('mensagem', '').strip()
        if not mensagem:
            return Response({'error': 'Mensagem obrigatória.'}, status=400)

        clientes = Cliente.objects.filter(aceita_sms=True).select_related('user')
        if not clientes.exists():
            return Response({'enviados': 0, 'erros': 0})

        sid   = settings.TWILIO_ACCOUNT_SID
        token_tw = settings.TWILIO_AUTH_TOKEN
        from_nr  = settings.TWILIO_FROM

        if not all([sid, token_tw, from_nr]):
            return Response({'error': 'Twilio não configurado no servidor.'}, status=500)

        client = TwilioClient(sid, token_tw)
        enviados = 0
        erros = 0

        for c in clientes:
            try:
                client.messages.create(
                    body=mensagem,
                    from_=from_nr,
                    to=c.telefone,
                )
                enviados += 1
            except Exception as e:
                print(f"Erro SMS para {c.telefone}: {e}")
                erros += 1

        return Response({'enviados': enviados, 'erros': erros})


# ---------------------------------------------------------------------------
# Editar perfil (email / telefone / aceita_sms)
# ---------------------------------------------------------------------------

class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        password = request.data.get('password', '')
        if not password or not user.check_password(password):
            return Response({'error': 'Password incorreta.'}, status=400)

        email    = request.data.get('email', '').strip().lower()
        telefone = request.data.get('telefone', '').strip()
        aceita_sms = request.data.get('aceita_sms', None)

        if email and email != user.email:
            if User.objects.exclude(pk=user.pk).filter(email=email).exists():
                return Response({'error': 'Já existe uma conta com este email.'}, status=400)
            user.email = email
            user.username = email
            user.save()

        try:
            cliente = user.cliente
        except Cliente.DoesNotExist:
            cliente = Cliente.objects.create(user=user, telefone='')

        if telefone:
            cliente.telefone = telefone
        if aceita_sms is not None:
            cliente.aceita_sms = aceita_sms
        cliente.save()

        return Response({
            'nome':       user.get_full_name(),
            'email':      user.email,
            'telefone':   cliente.telefone,
            'aceita_sms': cliente.aceita_sms,
        })


# ---------------------------------------------------------------------------
# Mudar password (autenticado)
# ---------------------------------------------------------------------------

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        atual = request.data.get('password_atual', '')
        nova  = request.data.get('password_nova', '')

        if not user.check_password(atual):
            return Response({'error': 'Password atual incorreta.'}, status=400)
        if len(nova) < 8:
            return Response({'error': 'A nova password deve ter pelo menos 8 caracteres.'}, status=400)

        user.set_password(nova)
        user.save()
        return Response({'message': 'Password alterada com sucesso.'})


# ---------------------------------------------------------------------------
# Recuperação de password (sem sessão)
# ---------------------------------------------------------------------------

class PasswordResetRequestView(APIView):
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        user = User.objects.filter(email=email).first()

        # resposta igual quer o email exista ou não (não revelar contas existentes)
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = f"{FRONTEND_URL}/pages/repor-password.html?uid={uid}&token={token}"

            _resend_send(
                to=user.email,
                subject="Repor password — ATXcyclingstore",
                html=f"""
                <div style="font-family:sans-serif;max-width:600px;margin:auto;color:#111">
                  <h2 style="color:#0077cc">Pedido de reposição de password</h2>
                  <p>Olá <strong>{user.get_full_name() or user.email}</strong>,</p>
                  <p>Recebemos um pedido para repor a password da tua conta na ATXcyclingstore.
                     Se não foste tu, podes ignorar este email.</p>
                  <a href="{reset_url}"
                     style="display:inline-block;background:#0077cc;color:white;padding:12px 24px;
                            border-radius:6px;text-decoration:none;font-weight:500;margin-top:16px">
                    Repor a minha password
                  </a>
                  <p style="margin-top:24px;font-size:13px;color:#888">
                    Este link é válido durante um período limitado por motivos de segurança.
                  </p>
                </div>""",
            )

        return Response({'message': 'Se o email existir, foi enviado um link de reposição.'})


class PasswordResetConfirmView(APIView):
    def post(self, request):
        uidb64 = request.data.get('uid', '')
        token  = request.data.get('token', '')
        nova   = request.data.get('password_nova', '')

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response({'error': 'Link inválido.'}, status=400)

        if not default_token_generator.check_token(user, token):
            return Response({'error': 'Link inválido ou expirado.'}, status=400)

        if len(nova) < 8:
            return Response({'error': 'A nova password deve ter pelo menos 8 caracteres.'}, status=400)

        user.set_password(nova)
        user.save()
        return Response({'message': 'Password reposta com sucesso.'})
