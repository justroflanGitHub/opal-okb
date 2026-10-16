
void __cdecl16near FUN_144d_1a1c(void)

{
  code *pcVar1;
  uint in_DX;
  uint extraout_DX;
  uint uVar2;
  int unaff_BP;
  uint *puVar3;
  uint *unaff_DI;
  undefined2 unaff_SS;
  undefined2 unaff_DS;
  bool bVar4;
  
  puVar3 = unaff_DI;
  while (puVar3[1] != *(uint *)(unaff_BP + 0xe)) {
    puVar3 = puVar3 + 2;
    if (puVar3 == (uint *)0x392) {
      return;
    }
  }
  uVar2 = in_DX + *puVar3;
  if (CARRY2(in_DX,*puVar3)) {
    return;
  }
  if ((puVar3 != unaff_DI) || (*(uint *)0x33c < uVar2)) {
    bVar4 = puVar3 < unaff_DI;
    if (puVar3 == unaff_DI) {
      bVar4 = ((uint)(CONCAT12(0xfff0 < uVar2,uVar2 + 0xf) >> 1) >> 3) + *(uint *)(unaff_BP + 0xe) <
              *(uint *)0x3b3;
    }
    pcVar1 = (code *)swi(0x21);
    (*pcVar1)();
    if (bVar4) {
      return;
    }
    uVar2 = extraout_DX;
    if (puVar3 == unaff_DI) {
      *(uint *)0x33c = extraout_DX;
    }
  }
  LOCK();
  *puVar3 = uVar2;
  UNLOCK();
  return;
}

