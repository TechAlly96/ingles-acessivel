# Inglês Acessível

Curso de inglês profissional **em áudio**, do básico ao avançado, feito para ser ouvido e acessível a pessoas com deficiência visual. Gratuito e de código aberto.

O aluno aprende como uma criança aprende a falar: ouvindo e repetindo. Depois de cada bipe vem um silêncio para falar a frase em voz alta.

- **25 partes de aula, 281 frases** do dia a dia de empresa: apresentações, reuniões, status, chamadas com clientes, apresentação de projetos, negociação, feedback e entrevista de emprego.
- **Três vozes**: narrador em português (`pt_BR-faber-medium`) e duas vozes em inglês nos diálogos (`en_US-ryan-medium` e `en_US-amy-medium`), todas do [Piper](https://github.com/OHF-Voice/piper1-gpl).
- **Imersão** (só inglês) no fim de cada nível e **desafio** (português → inglês) depois do avançado.
- Toca **com a tela apagada** e em segundo plano (elemento `<audio>` + Media Session), em sequência, como um cão-guia; funciona sem internet depois de baixar.

## Como funciona

| Pasta | O quê |
|---|---|
| `conteudo/curso.json` | Fonte da verdade: aulas, frases `[inglês, português]` e conversas `[a/b, inglês, português]`. Na explicação, `{texto}` entre chaves é narrado pela voz em inglês. |
| `gerador/montar_dados.py` | Transforma o curso em partes com capítulos e roteiro (fala, frase lenta, bipe + pausa para repetir). |
| `gerador/narrar.py` | Narra cada parte em um único `.ogg` com capítulos; cache por frase. `NARRAR_TESTE=1` troca as vozes por tons para testar a montagem. |
| `app/` | PWA sem dependências (o mesmo motor do Concurso Acessível). |
| `.github/workflows/publicar.yml` | A cada push: monta, narra só o que mudou e publica no GitHub Pages. |

Criado por **Marlon Myaggy, desenvolvedor Full Stack**.
