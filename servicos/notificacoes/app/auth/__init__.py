"""Conferência do token JWT.

Este serviço não faz login nem tem a tabela de usuários: ele só confere a
assinatura do token emitido pelo serviço de Usuários e lê dele o id e o perfil.
"""
