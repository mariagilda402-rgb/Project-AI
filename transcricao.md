# tactiq.io free youtube transcript
# No title found
# https://www.youtube.com/watch/Lc6h-Ks1llE

00:00:00.280 Se você clicou nesse vídeo, significa
00:00:02.000 que você também quer criar uma Vtuber
00:00:04.080 Ai, não é mesmo? Sim, uma Vituber AI,
00:00:06.040 tipo a Chum, a Neurossama ou até mesmo a
00:00:08.719 Elizabeth, que é a minha. E nesse vídeo
00:00:10.920 eu vou te ensinar a fazer a sua própria
00:00:12.599 Vituber AI de um jeito simples e fácil.
00:00:14.920 Então, sem enrolação, bora começar.
00:00:17.320 Primeiramente, os requisitos. VG o que
00:00:19.359 você vai precisar para rodar tudo isso.
00:00:21.600 O programa não é tão pesado, porém eu
00:00:23.439 recomendo algumas configurações
00:00:24.720 específicas para pelo menos ser viável.
00:00:27.640 As recomendações mínimas são uma placa
00:00:29.480 de vídeo GTX 1060, um processador i7 e
00:00:32.360 16 GB de RAM. Eu sei, eu sei, tudo isso
00:00:34.879 é meio caro, mas não tem o que eu possa
00:00:36.760 fazer. É, é basicamente tudo que você
00:00:38.719 vai precisar. Assim como a Neurossama e
00:00:41.039 a Shogun, Elizabeth é feita em Python
00:00:42.960 porque é fácil de mexer e também por ter
00:00:45.039 várias bibliotecas que podem auxiliar no
00:00:47.160 desenvolvimento do seu projeto. Eu
00:00:48.800 falarei mais sobre as bibliotecas mais
00:00:50.520 paraa frente, porém bora começar com os
00:00:52.239 três pontos básicos de toda a Vituber
00:00:54.000 AI, que no caso são o TTS, o
00:00:56.320 reconhecimento de voz e o LLM, a começar
00:00:59.320 pelo TTS ou text tr speed. Essa parte é
00:01:02.079 basicamente a voz da sua Vtuber Ai.
00:01:04.400 Assim como a Elizabeth tem a vozinha
00:01:05.880 dela, a sua também tem que ter, não é
00:01:07.400 mesmo? Nessa parte existem duas opções,
00:01:09.520 o Murph AI e o 11 Labs. Eu recomendo o
00:01:12.600 Murph AI por ele ser muito parecido com
00:01:14.520 o Eleven Labs, é claro, de uma maneira
00:01:16.280 mais simples, ele também é gratuito,
00:01:18.080 diferente do Eleven Labs, que tem uma PI
00:01:19.680 e paga. Outro ponto positivo do Morf é
00:01:21.920 que ele também tem a documentação
00:01:23.479 inteira lá dentro do site, como vocês
00:01:24.920 podem ver aí na tela. Em resumo, o que
00:01:26.799 eu fiz foi utilizar a API do Murfii para
00:01:29.320 gerar um arquivo de áudio. E esse
00:01:31.240 arquivo de áudio vai ser a voz dela.
00:01:33.000 Como todo mundo sabe, a resposta de uma
00:01:34.720 inteligência artificial, igual chattou
00:01:36.640 ou qualquer outro llável. E é essa
00:01:39.119 variável que será utilizada para fazer a
00:01:41.040 voz dela, no caso, como um guia. Em
00:01:43.200 resumo, o que você vai precisar fazer é
00:01:45.320 enviar a variável da resposta da sua
00:01:47.640 inteligência artificial, que você vai
00:01:49.360 pegar mais para frente, e enviar para o
00:01:51.799 site do Murf AI para que ele transforme
00:01:53.719 em um arquivo de áudio que
00:01:55.119 posteriormente será tocado com auxílio
00:01:56.759 da biblioteca P Game. Iniciando com a
00:01:59.079 função principal, como vocês podem ver
00:02:01.000 aqui, é a função de falar o texto. O
00:02:02.719 texto já é a resposta da sua
00:02:04.799 inteligência artificial, que em seguida
00:02:07.000 vai começar com uma condicional. Se o
00:02:09.520 caminho, no caso, tiver o áudio ainda
00:02:11.760 existente, ele vai remover o áudio para
00:02:13.480 poder gerar um novo em seguida, pegando
00:02:16.080 o texto e o ID da voz, no caso do site
00:02:18.879 Murfi, para em seguida criar o áudio e
00:02:22.440 tocar ele com auxílio do P Games. Esse
00:02:24.720 aqui é um exemplo do código que eu fiz,
00:02:26.599 porém dá para fazer de algumas outras
00:02:28.040 formas, só que no meu caso, esse daqui
00:02:29.840 foi a única que deu certo. Então eu vou
00:02:31.360 mostrar essa.
00:02:33.480 O segundo passo já é o reconhecimento de
00:02:35.319 voz. Nessa parte também tem duas opções.
00:02:37.239 Então bora lá. A primeira seria a
00:02:39.200 biblioteca Vosk para se caso você tenha
00:02:41.120 um microfone bem ruinzinho, aí ela é a
00:02:43.239 mais simples de você usar nesse caso. A
00:02:45.040 segunda é o speech recognition. Se você
00:02:46.720 tiver um microfone mais razoável, ela é
00:02:49.040 ótima para você usar. No caso do Vosk,
00:02:51.080 tem uma pequena limitação, pois esse
00:02:53.080 reconhecimento de voz necessita de um
00:02:54.640 modelo com um idioma. No caso, você
00:02:56.760 baixaria o idioma português. Porém, se
00:02:58.879 você baixa o idioma português, você não
00:03:00.400 pode falar em inglês com ela. Aí, quando
00:03:02.800 você for pronunciar o nome de algum jogo
00:03:04.760 ou alguma palavra em inglês específica
00:03:06.360 que você queira falar com ela, não vai
00:03:07.720 dar certo. Imagina, você vai jogar, sei
00:03:09.599 lá, Subnáutica com ela. Você vai falar
00:03:11.640 subnáutica, ela vai entender subir na
00:03:13.040 calça. Eu tô falando isso por
00:03:14.440 experiência própria, tá? Concluindo, o
00:03:16.120 que você vai precisar fazer é
00:03:17.280 basicamente pegar a resposta do que você
00:03:19.080 falou, que vai ser uma variável gerada
00:03:21.080 pelo speech recognition e usar como
00:03:23.480 resposta pra sua inteligência
00:03:24.840 artificial. vai enviar para ela, no caso
00:03:26.720 pro modelo IA, e ela vai rebater a
00:03:28.680 resposta.
00:03:30.640 E por último, e ao mesmo tempo o mais
00:03:32.920 importante, o Llou a inteligência
00:03:35.239 artificial da sua VTUtuber. Aqui você
00:03:37.360 também tem duas opções, é, não tem muito
00:03:39.560 para onde correr. Dessas opções tem a
00:03:41.680 fácil e a difícil. Vamos começar com a
00:03:43.840 fácil, que pode não agradar muitas
00:03:46.040 pessoas por ser realmente fácil demais,
00:03:48.200 porém é a mais acessível e a mais
00:03:50.439 simples que tem. Essa opção é chamada de
00:03:52.480 fine tuning. Eu espero ter pronunciado
00:03:54.519 corretamente. Trata-se de você pegar um
00:03:56.519 modelo já existente e apenas customizar
00:03:58.400 ele para que ele acha do jeito que você
00:03:59.680 quiser. Em resumo, você vai readaptar um
00:04:01.879 modelo já existente a partir de seu
00:04:03.640 prompt inicial. Primeiramente, você vai
00:04:05.560 precisar de um modelo de ya. Eu
00:04:06.959 recomendo os modelos OLAMAS. Eles são
00:04:08.439 muito fáceis de se utilizar e você pode
00:04:10.120 criar o seu próprio. Para isso, você
00:04:12.040 precisa instalar o OLAMA no seu PC. É
00:04:14.040 bem simples, é só você ir lá no site
00:04:15.480 deles e clicar na opção de download.
00:04:17.120 Após isso, você retorna ao site e vai na
00:04:19.720 opção de models. Lá tem vários modelos,
00:04:21.680 tem o Gema 3, tem alguns modelos GPT,
00:04:24.160 deepic e tudo mais. Após a escolha do
00:04:26.320 seu modelo, vá até o cmid do seu
00:04:28.199 computador e digita isso aí que tá na
00:04:30.240 tela. Tem esses dois, você usa um para
00:04:31.960 baixar e o outro para rodar o modelo se
00:04:34.000 caso você quiser. Após baixar o seu
00:04:35.960 modelo, agora vem uma parte que parece
00:04:37.919 difícil, mas não é não. Essa parte
00:04:39.600 trata-se de você usar um arquivo pon
00:04:41.360 model file para customizar o seu modelo.
00:04:43.400 Basicamente essa parte serve para você
00:04:45.320 definir como você quer que o seu modelo
00:04:46.919 já seja, né? A personalidade, os gostos,
00:04:49.479 o nome e por aí vai. A começar pelo
00:04:51.840 from, que é onde você vai colocar o nome
00:04:53.639 do modelo original que você quer
00:04:55.039 customizar. Em seguida, temos os
00:04:57.080 parâmetros. O parâmetro de temperatura é
00:04:59.520 basicamente o quão criativo você quer
00:05:02.160 que o seu modelo seja. Caso você coloque
00:05:04.199 um número muito alto, por exemplo, um
00:05:06.080 dois ou três, ele vai ser muito
00:05:07.639 criativo, porém impreciso. Em outras
00:05:09.880 palavras, ele mexe com a aleatoriedade
00:05:11.960 da resposta. Caso você queira um Jarvis
00:05:14.720 da vida, um assistente que vai ser só
00:05:16.479 para te auxiliar, você coloca um 0.7,
00:05:19.479 0.8. Eu recomendo esses números mais
00:05:21.560 baixos que dá uma resposta mais precisa,
00:05:24.039 ele não fica se perdendo na hora de
00:05:25.880 escrever as coisas. Ou você pode deixar
00:05:27.720 em um, que é um equilíbrio entre os
00:05:29.160 dois. Não fica muito exagerado para um,
00:05:30.759 mas também não fica muito técnico, sabe
00:05:32.440 como é, né? Essa parte aqui de baixo
00:05:34.199 pode parecer meio confuso, mas relaxa
00:05:36.039 que você não vai precisar se aprofundar
00:05:37.840 muito nessa parte. Em resumo, ele define
00:05:39.960 tokens especiais que o modelo deve parar
00:05:41.800 de gerar ao encontrar, né, esses essas
00:05:44.560 limitações, em outras palavras. Mas
00:05:46.400 relaxa que tá tudo certo essa parte.
00:05:48.039 Então vamos pro próximo. E por último,
00:05:50.199 mas também o mais fácil que tem, o
00:05:52.080 system. O sistem, de uma maneira simples
00:05:54.039 de se explicar, é onde você vai colocar
00:05:56.360 o nome, a personalidade, os gostos da
00:05:58.840 sua inteligência artificial. Em outras
00:06:00.800 palavras, como você quer que ela seja.
00:06:02.720 Por exemplo, você quer que ela seja uma
00:06:04.639 maga caçadora de outra realidade que
00:06:06.680 veio pra Terra comer pastel? Agora vem a
00:06:09.680 opção difícil que é criar um do zero. Eu
00:06:11.840 não tenho muito do que dizer sobre essa
00:06:13.840 parte porque nem eu terminei o meu
00:06:15.639 modelo do zero. Ele ainda tá em fase de
00:06:17.199 desenvolvimento e eu pretendo lançar ele
00:06:19.639 quando tiver pronto e em algum especial
00:06:21.800 aí do canal, provavelmente lá pros 1000
00:06:23.479 inscritos, talvez, né? Quem sabe? Mas eu
00:06:25.400 ainda posso te dizer o caminho que eu
00:06:27.000 estou seguindo. Para o primeiro passo,
00:06:28.560 eu recomendo você estudar algumas
00:06:30.160 bibliotecas do Python, como por exemplo
00:06:31.919 Pythort, Tensor Flow, NLTK, porque aí
00:06:34.479 você vai precisar de uma coisa chamado
00:06:35.759 rede neural. Para quem não sabe, o Chat
00:06:37.840 GPT, Grock, Queen ou qualquer outra
00:06:40.479 inteligência artificial que é um LLM são
00:06:42.919 baseados em redes neurais de arquitetura
00:06:44.840 do Transformer. Não, não é Transformer
00:06:46.880 Optimus Prime. Você não vai fazer o
00:06:48.199 Bumblebee, [ __ ]
00:06:50.319 Ah, eu sou [ __ ] Mas voltando a um
00:06:52.639 assunto que realmente importa, eu
00:06:54.160 recomendo vocês irem atrás de alguns
00:06:55.720 gitubs sobre o assunto. Lá tem bastante
00:06:57.599 informação e é muito extenso. É sério, é
00:06:59.720 quase que inteiramente documentado. Mas
00:07:01.879 em resumo, a biblioteca que eu mais
00:07:03.800 recomendo você pesquisar sobre é o P
00:07:05.440 tort. Ela é muito boa, é maneiro demais
00:07:07.560 fazer redes neurais nela, além de ser
00:07:09.360 fácil, já que ele usa a arquitetura do
00:07:10.680 Transformer. E no futuro eu pretendo
00:07:12.479 mostrar mais sobre criar um LLM do zero.
00:07:14.879 O problema é que meu canal não é de
00:07:16.120 programação, então acho que a maior
00:07:17.680 parte do meu público não ia se
00:07:18.680 interessar por isso, porém é legal de
00:07:20.879 fazer.
00:07:22.919 A parte do modelo, cara, essa é a mais
00:07:24.720 fácil que tem. Eh, tem alguns sites com
00:07:27.280 modelos gratuitos ou você pode só pagar
00:07:29.000 alguém para fazer um para você. E para
00:07:30.800 sincronizar a voz da IA com o modelo, é
00:07:33.199 só baixar uma extensão, no caso, essa
00:07:35.199 daqui, ó, o VTS desktop. E aí é só
00:07:37.400 selecionar o parâmetro de movimento com
00:07:39.360 o áudio do desktop. É meio provisório,
00:07:41.599 mas serve por enquanto.
